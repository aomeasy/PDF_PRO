import streamlit as st
import streamlit.components.v1 as components
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image
import io
import json
import base64

# Import font module with error handling
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
    FONTS_AVAILABLE = True
except ImportError:
    FONTS_AVAILABLE = False

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="PDF Manager Pro - Interactive",
    page_icon="📄",
    layout="wide"
)

# ฟังก์ชันสำหรับแก้ไข PDF ด้วย text elements
def edit_pdf_with_elements(pdf_file, text_elements):
    """สร้าง PDF ใหม่โดยเพิ่ม text overlay"""
    reader = PdfReader(pdf_file)
    writer = PdfWriter()
    width, height = A4
    
    # จัดกลุ่ม elements ตามหน้า
    elements_by_page = {}
    for element in text_elements:
        page = element.get('page', 1)
        if page not in elements_by_page:
            elements_by_page[page] = []
        elements_by_page[page].append(element)
    
    # ประมวลผลแต่ละหน้า
    for page_num, page in enumerate(reader.pages, start=1):
        if page_num in elements_by_page:
            # สร้าง overlay สำหรับหน้านี้
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)
            
            for element in elements_by_page[page_num]:
                text = element.get('text', '')
                x = float(element.get('x', 50))
                y = float(element.get('y', 700))
                font_size = int(element.get('fontSize', 16))
                font_name = element.get('font', 'Helvetica')
                color = element.get('color', '#000000')
                
                # แปลงสี hex เป็น RGB
                color = color.lstrip('#')
                r, g, b = tuple(int(color[i:i+2], 16)/255 for i in (0, 2, 4))
                can.setFillColorRGB(r, g, b)
                
                # ตั้งค่าฟอนต์
                try:
                    can.setFont(font_name, font_size)
                except:
                    can.setFont('Helvetica', font_size)
                
                # แปลง y coordinate (PDF ใช้ bottom-left เป็น origin)
                y_pdf = height - y - font_size
                can.drawString(x, y_pdf, text)
            
            can.save()
            packet.seek(0)
            
            # รวม overlay กับหน้าต้นฉบับ
            overlay_pdf = PdfReader(packet)
            page.merge_page(overlay_pdf.pages[0])
        
        writer.add_page(page)
    
    # สร้าง output
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# ฟังก์ชัน Interactive Editor Component
def interactive_pdf_editor():
    """แสดง Interactive PDF Editor"""
    
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .editor-container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .toolbar {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 10px 10px 0 0;
                color: white;
            }
            .toolbar h2 { margin-bottom: 15px; }
            .controls {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 10px;
                margin-bottom: 15px;
            }
            .controls input, .controls select {
                padding: 8px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            textarea {
                width: 100%;
                padding: 10px;
                border: none;
                border-radius: 5px;
                resize: vertical;
                min-height: 60px;
                font-family: inherit;
            }
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
            }
            .btn-add {
                background: white;
                color: #667eea;
                width: 100%;
                margin-top: 10px;
            }
            .btn-add:hover {
                background: #f0f0f0;
            }
            .btn-save {
                background: #28a745;
                color: white;
                width: 100%;
                margin-top: 10px;
            }
            .btn-clear {
                background: #dc3545;
                color: white;
                width: 100%;
            }
            .canvas-wrapper {
                padding: 20px;
                min-height: 600px;
            }
            #canvas {
                width: 595px;
                height: 842px;
                border: 2px solid #ddd;
                margin: 0 auto;
                position: relative;
                background: white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .text-element {
                position: absolute;
                cursor: move;
                padding: 5px;
                border: 2px dashed transparent;
                user-select: none;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .text-element:hover {
                border-color: #667eea;
                background: rgba(102, 126, 234, 0.1);
            }
            .text-element.selected {
                border-color: #667eea;
                background: rgba(102, 126, 234, 0.15);
            }
            .delete-btn {
                position: absolute;
                top: -12px;
                right: -12px;
                width: 24px;
                height: 24px;
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 50%;
                cursor: pointer;
                display: none;
                font-size: 14px;
                line-height: 1;
            }
            .text-element:hover .delete-btn {
                display: block;
            }
            .resize-handle {
                position: absolute;
                bottom: -5px;
                right: -5px;
                width: 12px;
                height: 12px;
                background: #667eea;
                cursor: nwse-resize;
                border-radius: 50%;
                display: none;
            }
            .text-element:hover .resize-handle {
                display: block;
            }
            .info-box {
                background: #e7f3ff;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 15px;
                border-left: 4px solid #667eea;
            }
        </style>
    </head>
    <body>
        <div class="editor-container">
            <div class="toolbar">
                <h2>✏️ PDF Interactive Editor</h2>
                <div class="info-box">
                    💡 <strong>วิธีใช้:</strong> พิมพ์ข้อความ → กด "เพิ่มข้อความ" → ลากวางตำแหน่ง → ลากมุมเพื่อปรับขนาด
                </div>
                
                <textarea id="textInput" placeholder="พิมพ์ข้อความที่ต้องการเพิ่ม..."></textarea>
                
                <div class="controls">
                    <select id="fontSelect">
                        <option value="Arial">Arial</option>
                        <option value="Helvetica">Helvetica</option>
                        <option value="Times New Roman">Times</option>
                        <option value="Courier New">Courier</option>
                    </select>
                    <input type="number" id="fontSize" value="16" min="8" max="72" placeholder="ขนาด">
                    <input type="color" id="textColor" value="#000000">
                </div>
                
                <button class="btn btn-add" onclick="addText()">➕ เพิ่มข้อความ</button>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <button class="btn btn-clear" onclick="clearAll()">🗑️ ล้างทั้งหมด</button>
                    <button class="btn btn-save" onclick="savePDF()">💾 บันทึกและสร้าง PDF</button>
                </div>
            </div>
            
            <div class="canvas-wrapper">
                <div id="canvas"></div>
            </div>
        </div>

        <script>
            let textElements = [];
            let elementCounter = 0;
            let selectedElement = null;
            let isDragging = false;
            let isResizing = false;
            let startX, startY, startLeft, startTop, startFontSize;

            function addText() {
                const text = document.getElementById('textInput').value;
                if (!text.trim()) {
                    alert('กรุณาใส่ข้อความ');
                    return;
                }

                const element = {
                    id: ++elementCounter,
                    text: text,
                    x: 50,
                    y: 50,
                    fontSize: parseInt(document.getElementById('fontSize').value),
                    font: document.getElementById('fontSelect').value,
                    color: document.getElementById('textColor').value,
                    page: 1
                };

                textElements.push(element);
                createTextElement(element);
                document.getElementById('textInput').value = '';
            }

            function createTextElement(el) {
                const canvas = document.getElementById('canvas');
                const div = document.createElement('div');
                div.className = 'text-element';
                div.id = 'text-' + el.id;
                div.style.left = el.x + 'px';
                div.style.top = el.y + 'px';
                div.style.fontSize = el.fontSize + 'px';
                div.style.fontFamily = el.font;
                div.style.color = el.color;
                div.textContent = el.text;

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-btn';
                deleteBtn.textContent = '×';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteText(el.id);
                };
                div.appendChild(deleteBtn);

                const resizeHandle = document.createElement('div');
                resizeHandle.className = 'resize-handle';
                div.appendChild(resizeHandle);

                div.addEventListener('mousedown', (e) => startDrag(e, el));
                resizeHandle.addEventListener('mousedown', (e) => startResize(e, el));

                canvas.appendChild(div);
            }

            function startDrag(e, el) {
                if (e.target.className === 'resize-handle') return;
                selectedElement = el;
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                startLeft = el.x;
                startTop = el.y;
                
                const div = document.getElementById('text-' + el.id);
                div.classList.add('selected');
            }

            function startResize(e, el) {
                e.stopPropagation();
                selectedElement = el;
                isResizing = true;
                startY = e.clientY;
                startFontSize = el.fontSize;
            }

            document.addEventListener('mousemove', (e) => {
                if (isDragging && selectedElement) {
                    const dx = e.clientX - startX;
                    const dy = e.clientY - startY;
                    
                    selectedElement.x = Math.max(0, Math.min(startLeft + dx, 550));
                    selectedElement.y = Math.max(0, Math.min(startTop + dy, 800));
                    
                    const div = document.getElementById('text-' + selectedElement.id);
                    div.style.left = selectedElement.x + 'px';
                    div.style.top = selectedElement.y + 'px';
                }
                
                if (isResizing && selectedElement) {
                    const dy = e.clientY - startY;
                    const newSize = Math.max(8, Math.min(72, startFontSize + dy));
                    
                    selectedElement.fontSize = newSize;
                    const div = document.getElementById('text-' + selectedElement.id);
                    div.style.fontSize = newSize + 'px';
                }
            });

            document.addEventListener('mouseup', () => {
                if (selectedElement) {
                    const div = document.getElementById('text-' + selectedElement.id);
                    div.classList.remove('selected');
                }
                isDragging = false;
                isResizing = false;
                selectedElement = null;
            });

            function deleteText(id) {
                textElements = textElements.filter(el => el.id !== id);
                const div = document.getElementById('text-' + id);
                if (div) div.remove();
            }

            function clearAll() {
                if (confirm('ลบข้อความทั้งหมด?')) {
                    textElements = [];
                    document.getElementById('canvas').innerHTML = '';
                }
            }

            function savePDF() {
                if (textElements.length === 0) {
                    alert('กรุณาเพิ่มข้อความก่อน');
                    return;
                }
                
                // ส่งข้อมูลกลับไปยัง Streamlit
                window.parent.postMessage({
                    type: 'pdf_data',
                    elements: textElements
                }, '*');
            }
        </script>
    </body>
    </html>
    """
    
    # แสดง component
    components.html(html_code, height=1000, scrolling=True)

# Main App
st.title("📄 PDF Manager Pro - Interactive Edition")

# Sidebar
feature = st.sidebar.radio(
    "เลือกฟังก์ชัน",
    ["✏️ แก้ไข PDF (Interactive)", "🔗 รวมไฟล์ PDF", "✂️ แบ่งไฟล์ PDF"]
)

# Interactive PDF Editor
if feature == "✏️ แก้ไข PDF (Interactive)":
    st.header("✏️ แก้ไข PDF แบบ Interactive")
    
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf")
    
    if uploaded_file:
        # เก็บไฟล์ใน session state
        if 'pdf_file' not in st.session_state:
            st.session_state.pdf_file = uploaded_file
        
        st.success(f"✅ อัปโหลดไฟล์สำเร็จ: {uploaded_file.name}")
        
        # แสดง Interactive Editor
        st.markdown("---")
        interactive_pdf_editor()
        
        # รับข้อมูลจาก JavaScript (ใช้ session state แทน)
        if 'text_elements' not in st.session_state:
            st.session_state.text_elements = []
        
        # แสดงข้อมูลที่บันทึก
        if st.session_state.text_elements:
            st.markdown("---")
            st.subheader("📝 ข้อมูลที่บันทึก")
            st.json(st.session_state.text_elements)
            
            if st.button("🎨 สร้าง PDF จากข้อมูลนี้", type="primary"):
                with st.spinner("กำลังสร้าง PDF..."):
                    edited_pdf = edit_pdf_with_elements(
                        uploaded_file,
                        st.session_state.text_elements
                    )
                    
                    st.success("✅ สร้าง PDF สำเร็จ!")
                    st.download_button(
                        label="📥 ดาวน์โหลด PDF",
                        data=edited_pdf,
                        file_name="edited.pdf",
                        mime="application/pdf"
                    )
        
        # Manual input (fallback)
        with st.expander("🔧 หรือเพิ่มข้อมูลด้วยมือ"):
            text = st.text_area("ข้อความ")
            col1, col2, col3 = st.columns(3)
            with col1:
                x = st.number_input("X", 0, 600, 50)
            with col2:
                y = st.number_input("Y", 0, 800, 100)
            with col3:
                size = st.number_input("ขนาด", 8, 72, 16)
            
            if st.button("➕ เพิ่ม"):
                if 'text_elements' not in st.session_state:
                    st.session_state.text_elements = []
                st.session_state.text_elements.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'fontSize': size,
                    'font': 'Helvetica',
                    'color': '#000000',
                    'page': 1
                })
                st.rerun()

# รวมไฟล์ PDF
elif feature == "🔗 รวมไฟล์ PDF":
    st.header("รวมหลาย PDF เป็นไฟล์เดียว")
    uploaded_files = st.file_uploader(
        "อัปโหลดไฟล์ PDF (หลายไฟล์)",
        type="pdf",
        accept_multiple_files=True
    )
    
    if uploaded_files and len(uploaded_files) > 1:
        if st.button("รวมไฟล์"):
            from PyPDF2 import PdfMerger
            merger = PdfMerger()
            for pdf in uploaded_files:
                merger.append(pdf)
            
            output = io.BytesIO()
            merger.write(output)
            merger.close()
            output.seek(0)
            
            st.success("✅ รวมไฟล์สำเร็จ!")
            st.download_button(
                "📥 ดาวน์โหลด",
                data=output,
                file_name="merged.pdf",
                mime="application/pdf"
            )

# แบ่งไฟล์ PDF  
elif feature == "✂️ แบ่งไฟล์ PDF":
    st.header("แบ่ง PDF ตามช่วงหน้า")
    st.info("ฟีเจอร์นี้กำลังพัฒนา...")
