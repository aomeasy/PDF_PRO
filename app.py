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
import os

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

# ──────────────────────────────────────────────────────────────────────────────
# ฟังก์ชันสำหรับแก้ไข PDF ด้วย text elements (รับเป็น bytes)
# ──────────────────────────────────────────────────────────────────────────────
def edit_pdf_with_elements(pdf_bytes: bytes, text_elements):
    """สร้าง PDF ใหม่โดยเพิ่ม text overlay"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    width, height = A4

    # จัดกลุ่ม elements ตามหน้า
    elements_by_page = {}
    for element in text_elements:
        page_idx = int(element.get('page', 1))
        elements_by_page.setdefault(page_idx, []).append(element)

    # ประมวลผลแต่ละหน้า
    for page_num, page in enumerate(reader.pages, start=1):
        if page_num in elements_by_page:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)

            for element in elements_by_page[page_num]:
                text = element.get('text', '')
                x = float(element.get('x', 50))
                y = float(element.get('y', 700))
                font_size = int(element.get('fontSize', 16))
                font_name = element.get('font', 'Helvetica')
                color = element.get('color', '#000000')

                # แปลงสี hex → RGB
                try:
                    c = color.lstrip('#')
                    r, g, b = (int(c[i:i+2], 16)/255 for i in (0, 2, 4))
                    can.setFillColorRGB(r, g, b)
                except Exception:
                    can.setFillColorRGB(0, 0, 0)

                # ตั้งค่าฟอนต์ (ลอง TH Sarabun ถ้ามี)
                try:
                    if font_name in ["THSarabunPSK", "THSarabunNew"] and FONTS_AVAILABLE:
                        font_path = f"fonts/{font_name}.ttf"
                        if os.path.exists(font_path):
                            pdfmetrics.registerFont(TTFont(font_name, font_path))
                            can.setFont(font_name, font_size)
                        else:
                            can.setFont('Helvetica', font_size)
                    else:
                        can.setFont(font_name, font_size)
                except Exception:
                    can.setFont('Helvetica', font_size)

                # PDF origin เป็นมุมล่างซ้าย
                y_pdf = height - y - font_size
                can.drawString(x, y_pdf, text)

            can.save()
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            page.merge_page(overlay_pdf.pages[0])

        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out

# ──────────────────────────────────────────────────────────────────────────────
# ฟังก์ชัน Interactive Editor Component (ส่ง pdf เป็น bytes → base64 → Uint8Array ใน JS)
# ──────────────────────────────────────────────────────────────────────────────
def interactive_pdf_editor(pdf_bytes: bytes | None = None):
    """แสดง Interactive PDF Editor (เรนเดอร์หน้าแรกด้วย pdf.js)"""

    pdf_base64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }}
            .editor-container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .toolbar {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 10px 10px 0 0;
                color: white;
            }}
            .toolbar h2 {{ margin-bottom: 15px; }}
            .controls {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 10px;
                margin-bottom: 15px;
            }}
            .controls input, .controls select {{
                padding: 8px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }}
            textarea {{
                width: 100%;
                padding: 10px;
                border: none;
                border-radius: 5px;
                resize: vertical;
                min-height: 60px;
                font-family: inherit;
            }}
            .btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
            }}
            .btn-add {{
                background: white;
                color: #667eea;
                width: 100%;
                margin-top: 10px;
            }}
            .btn-add:hover {{ background: #f0f0f0; }}
            .btn-save {{
                background: #28a745;
                color: white;
                width: 100%;
                margin-top: 10px;
            }}
            .btn-clear {{ background: #dc3545; color: white; width: 100%; }}
            .canvas-wrapper {{ padding: 20px; min-height: 600px; overflow: auto; }}
            #canvas {{
                width: 595px;
                height: 842px;
                border: 2px solid #ddd;
                margin: 0 auto;
                position: relative;
                background: white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            #pdfCanvas {{
                position: absolute;
                top: 0; left: 0;
                width: 595px; height: 842px;
                pointer-events: none;
            }}
            .text-element {{
                position: absolute;
                cursor: move;
                padding: 5px;
                border: 2px dashed transparent;
                user-select: none;
                white-space: pre-wrap;
                word-wrap: break-word;
                z-index: 10;
            }}
            .text-element:hover {{ border-color: #667eea; background: rgba(102,126,234,0.1); }}
            .text-element.selected {{ border-color: #667eea; background: rgba(102,126,234,0.15); }}
            .delete-btn {{
                position: absolute; top: -12px; right: -12px;
                width: 24px; height: 24px; background: #dc3545; color: white;
                border: none; border-radius: 50%; cursor: pointer; display: none; font-size: 14px; line-height: 1;
            }}
            .text-element:hover .delete-btn {{ display: block; }}
            .resize-handle {{
                position: absolute; bottom: -5px; right: -5px;
                width: 12px; height: 12px; background: #667eea;
                cursor: nwse-resize; border-radius: 50%; display: none;
            }}
            .text-element:hover .resize-handle {{ display: block; }}
            .info-box {{
                background: #e7f3ff; padding: 15px; border-radius: 5px; margin-bottom: 15px;
                border-left: 4px solid #667eea; color: #333; font-weight: 500;
            }}
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
                        <option value="Helvetica">Helvetica</option>
                        <option value="Times-Roman">Times New Roman</option>
                        <option value="Courier">Courier</option>
                        <option value="THSarabunPSK">TH Sarabun PSK</option>
                        <option value="THSarabunNew">TH Sarabun New</option>
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
                <div id="canvas">
                    <canvas id="pdfCanvas" width="595" height="842"></canvas>
                </div>
            </div>
        </div>

        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
        <script>
            let textElements = [];
            let elementCounter = 0;
            let selectedElement = null;
            let isDragging = false;
            let isResizing = false;
            let startX, startY, startLeft, startTop, startFontSize;

            // --- helper: base64 -> Uint8Array ---
            function base64ToUint8Array(base64) {{
                const raw = atob(base64);
                const len = raw.length;
                const arr = new Uint8Array(len);
                for (let i = 0; i < len; i++) arr[i] = raw.charCodeAt(i);
                return arr;
            }}

            // โหลด PDF (หน้าแรก) ด้วย pdf.js
            const pdfData = '{pdf_base64}';
            if (pdfData) {{
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                const uint8 = base64ToUint8Array(pdfData);
                const loadingTask = pdfjsLib.getDocument({{ data: uint8 }});
                loadingTask.promise.then((pdf) => {{
                    return pdf.getPage(1).then((page) => {{
                        const canvas = document.getElementById('pdfCanvas');
                        const ctx = canvas.getContext('2d');

                        // คำนวณสเกลให้พอดี 595x842
                        const unscaled = page.getViewport({{ scale: 1.0 }});
                        const scale = Math.min(595 / unscaled.width, 842 / unscaled.height);
                        const viewport = page.getViewport({{ scale }});

                        canvas.width = viewport.width;
                        canvas.height = viewport.height;

                        const renderContext = {{
                            canvasContext: ctx,
                            viewport: viewport
                        }};
                        return page.render(renderContext).promise;
                    }});
                }}).catch(err => {{
                    console.error('pdf.js error:', err);
                }});
            }}

            function addText() {{
                const text = document.getElementById('textInput').value;
                if (!text.trim()) {{ alert('กรุณาใส่ข้อความ'); return; }}

                const element = {{
                    id: ++elementCounter,
                    text,
                    x: 50,
                    y: 50,
                    fontSize: parseInt(document.getElementById('fontSize').value),
                    font: document.getElementById('fontSelect').value,
                    color: document.getElementById('textColor').value,
                    page: 1
                }};
                textElements.push(element);
                createTextElement(element);
                document.getElementById('textInput').value = '';
            }}

            function createTextElement(el) {{
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
                deleteBtn.onclick = (e) => {{ e.stopPropagation(); deleteText(el.id); }};
                div.appendChild(deleteBtn);

                const resizeHandle = document.createElement('div');
                resizeHandle.className = 'resize-handle';
                div.appendChild(resizeHandle);

                div.addEventListener('mousedown', (e) => startDrag(e, el));
                resizeHandle.addEventListener('mousedown', (e) => startResize(e, el));

                canvas.appendChild(div);
            }}

            function startDrag(e, el) {{
                if (e.target.className === 'resize-handle') return;
                selectedElement = el;
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                startLeft = el.x;
                startTop = el.y;
                document.getElementById('text-' + el.id).classList.add('selected');
            }}

            function startResize(e, el) {{
                e.stopPropagation();
                selectedElement = el;
                isResizing = true;
                startY = e.clientY;
                startFontSize = el.fontSize;
            }}

            document.addEventListener('mousemove', (e) => {{
                if (isDragging && selectedElement) {{
                    const dx = e.clientX - startX;
                    const dy = e.clientY - startY;
                    selectedElement.x = Math.max(0, Math.min(startLeft + dx, 550));
                    selectedElement.y = Math.max(0, Math.min(startTop + dy, 800));
                    const div = document.getElementById('text-' + selectedElement.id);
                    div.style.left = selectedElement.x + 'px';
                    div.style.top = selectedElement.y + 'px';
                }}
                if (isResizing && selectedElement) {{
                    const dy = e.clientY - startY;
                    const newSize = Math.max(8, Math.min(72, startFontSize + dy));
                    selectedElement.fontSize = newSize;
                    document.getElementById('text-' + selectedElement.id).style.fontSize = newSize + 'px';
                }}
            }});

            document.addEventListener('mouseup', () => {{
                if (selectedElement) {{
                    document.getElementById('text-' + selectedElement.id).classList.remove('selected');
                }}
                isDragging = false;
                isResizing = false;
                selectedElement = null;
            }});

            function deleteText(id) {{
                textElements = textElements.filter(el => el.id !== id);
                const div = document.getElementById('text-' + id);
                if (div) div.remove();
            }}

            function clearAll() {{
                if (confirm('ลบข้อความทั้งหมด?')) {{
                    textElements.forEach(el => {{
                        const div = document.getElementById('text-' + el.id);
                        if (div) div.remove();
                    }});
                    textElements = [];
                }}
            }}

            function savePDF() {{
                if (textElements.length === 0) {{ alert('กรุณาเพิ่มข้อความก่อน'); return; }}
                window.parent.postMessage({{
                    type: 'pdf_data',
                    elements: textElements
                }}, '*');
                alert('✅ บันทึกข้อมูลสำเร็จ! กรุณากดปุ่ม "สร้าง PDF" ด้านล่าง');
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=1000, scrolling=True)

# ──────────────────────────────────────────────────────────────────────────────
# Main App
# ──────────────────────────────────────────────────────────────────────────────
st.title("📄 PDF Manager Pro - Interactive Edition")
st.markdown("### แก้ไข PDF แบบมืออาชีพ - ลาก วาง ปรับขนาดได้อย่างอิสระ")

# Sidebar
feature = st.sidebar.radio(
    "เลือกฟังก์ชัน",
    ["✏️ แก้ไข PDF (Interactive)", "🔗 รวมไฟล์ PDF"]
)

# ──────────────────────────────────────────────────────────────────────────────
# Interactive PDF Editor
# ──────────────────────────────────────────────────────────────────────────────
if feature == "✏️ แก้ไข PDF (Interactive)":
    st.header("✏️ แก้ไข PDF แบบ Interactive")

    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="edit_pdf")

    if uploaded_file:
        # อ่านเป็น bytes ครั้งเดียว ป้องกัน pointer เพี้ยน
        pdf_bytes = uploaded_file.getvalue()

        # ใช้ bytes สร้าง reader เพื่อบอกจำนวนหน้า
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)

        st.success(f"✅ อัปโหลดไฟล์สำเร็จ: {uploaded_file.name}")
        st.info(f"📄 ไฟล์มี {total_pages} หน้า")

        # แสดง Interactive Editor พร้อม PDF
        st.markdown("---")
        st.subheader("🎨 Interactive Editor")
        interactive_pdf_editor(pdf_bytes)  # ส่ง bytes เข้า editor

        # รับข้อมูลจาก JavaScript (ถ้าต้องการดัก message เพิ่มให้ใช้ components iframe advanced – ข้ามในเวอร์ชันนี้)
        st.markdown("---")
        st.subheader("📝 เพิ่มข้อมูลเพื่อสร้าง PDF")

        # Manual input สำหรับเพิ่มข้อมูล
        with st.expander("➕ เพิ่มข้อความด้วยมือ (หรือใช้ Interactive Editor ด้านบน)", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                text = st.text_area("ข้อความ", key="manual_text")
                x = st.number_input("ตำแหน่ง X", 0, 600, 50, key="manual_x")
                y = st.number_input("ตำแหน่ง Y", 0, 800, 100, key="manual_y")
            with col2:
                font = st.selectbox("ฟอนต์", ["Helvetica", "Times-Roman", "Courier", "THSarabunPSK", "THSarabunNew"], key="manual_font")
                size = st.number_input("ขนาด", 8, 72, 16, key="manual_size")
                color = st.color_picker("สี", "#000000", key="manual_color")

            if st.button("➕ เพิ่มข้อความนี้"):
                if text:
                    st.session_state.setdefault('text_elements', [])
                    st.session_state.text_elements.append({
                        'text': text,
                        'x': x,
                        'y': y,
                        'fontSize': size,
                        'font': font,
                        'color': color,
                        'page': 1
                    })
                    st.success("✅ เพิ่มข้อความแล้ว!")
                    st.rerun()

        # แสดงข้อมูลที่บันทึก
        if 'text_elements' in st.session_state and st.session_state.text_elements:
            st.markdown("---")
            st.subheader("📋 ข้อความที่เพิ่มไว้")

            for i, el in enumerate(st.session_state.text_elements):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(f"{i+1}. {el['text'][:50]}... (ตำแหน่ง: {el['x']}, {el['y']} | ขนาด: {el['fontSize']}px)")
                with col2:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.text_elements.pop(i)
                        st.rerun()

            with st.expander("📊 ดูข้อมูล JSON"):
                st.json(st.session_state.text_elements)

            # ปุ่มสร้าง PDF
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
                    st.session_state.text_elements = []
                    st.rerun()
            with col2:
                if st.button("🎨 สร้าง PDF", type="primary", use_container_width=True):
                    with st.spinner("กำลังสร้าง PDF..."):
                        try:
                            edited_pdf = edit_pdf_with_elements(
                                pdf_bytes,
                                st.session_state.text_elements
                            )
                            st.success("✅ สร้าง PDF สำเร็จ!")
                            st.download_button(
                                label="📥 ดาวน์โหลด PDF ที่แก้ไขแล้ว",
                                data=edited_pdf,
                                file_name="edited_" + uploaded_file.name,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        else:
            st.info("👆 ใช้ Interactive Editor ด้านบนเพื่อเพิ่มข้อความ หรือเพิ่มด้วยมือในส่วน 'เพิ่มข้อความด้วยมือ'")

# ──────────────────────────────────────────────────────────────────────────────
# รวมไฟล์ PDF
# ──────────────────────────────────────────────────────────────────────────────
elif feature == "🔗 รวมไฟล์ PDF":
    st.header("รวมหลาย PDF เป็นไฟล์เดียว")
    uploaded_files = st.file_uploader(
        "อัปโหลดไฟล์ PDF (หลายไฟล์)",
        type="pdf",
        accept_multiple_files=True,
        key="merge_files"
    )

    if uploaded_files and len(uploaded_files) > 1:
        st.info(f"เลือก {len(uploaded_files)} ไฟล์")

        if st.button("รวมไฟล์"):
            with st.spinner("กำลังรวมไฟล์..."):
                merger = PdfMerger()
                for pdf in uploaded_files:
                    merger.append(io.BytesIO(pdf.getvalue()))
                output = io.BytesIO()
                merger.write(output)
                merger.close()
                output.seek(0)

                st.success("✅ รวมไฟล์สำเร็จ!")
                st.download_button(
                    "📥 ดาวน์โหลดไฟล์ที่รวมแล้ว",
                    data=output,
                    file_name="merged.pdf",
                    mime="application/pdf"
                )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>พัฒนาด้วย ❤️ โดยใช้ Streamlit | © 2025 PDF Manager Pro - Interactive Edition</p>
    </div>
    """,
    unsafe_allow_html=True
)
