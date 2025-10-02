import streamlit as st
import streamlit.components.v1 as components
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io
import json
import base64
import os

# ------------------------------------------------------------
# 1. SETUP & CONFIGURATION (Page Config & CSS)
# ------------------------------------------------------------

# Font config (for server-side PDF generation)
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
    # Assume font files (THSarabunPSK.ttf, THSarabunNew.ttf) are in a 'fonts/' directory
    FONTS_AVAILABLE = True
except ImportError:
    FONTS_AVAILABLE = False

# Set page config (Layout, Title, Hide Streamlit "hamburger" menu)
st.set_page_config(
    page_title="PDF Manager Pro - SPA", 
    page_icon="📄", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (ตามที่ระบุ: ปรับปรุงสไตล์และซ่อนเมนู hamburger)
st.markdown("""
<style>
/* 1. Hide Streamlit 'hamburger' menu & footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* Custom styles for modern UI */
:root{
    --bg:#f6f7fb; --card:#ffffff; --border:#e5e7eb;
    --text:#0f172a; --muted:#64748b;
    --primary:#111827; /* near-black */
    --accent:#2563eb;  /* blue-600 */
    --success:#10b981; /* emerald-500 */
    --danger:#ef4444;  /* red-500 */
}
html, body { 
    background: var(--bg); 
    /* เพิ่มฟอนต์: ให้ใช้ฟอนต์ที่อ่านง่าย หรือฟอนต์ที่ท่านติดตั้งไว้ */
    font-family: 'Sarabun', 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}
.block-container { padding-top: 14px; }

/* Header Card: คงไว้ */
.header-card{
    background: var(--card); color: var(--text);
    border: 1px solid var(--border);
    border-radius: 16px; padding: 18px 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,.06);
}
.header-card h1{ margin:0; font-size:1.35rem; font-weight:800; letter-spacing:.2px; }
.header-card p{ margin:6px 0 0; color:var(--muted); }

/* Sidebar Button Customization (เพื่อให้ดูเป็น SPA Navigation) */
/* This targets the generated buttons in the custom sidebar logic */
div[data-testid="stSidebar"] button {
    border: none;
    background: transparent;
    color: var(--text);
    padding: 10px 16px;
    margin: 4px 0;
    width: 100%;
    text-align: left;
    border-radius: 8px;
    font-weight: 600;
}
div[data-testid="stSidebar"] button:hover {
    background: #eef1f6;
    color: var(--accent);
}
/* Style the currently active page button */
div[data-testid="stSidebar"] button.active-page {
    background: var(--accent);
    color: #ffffff;
}
div[data-testid="stSidebar"] button.active-page:hover {
    background: #1e40af; /* slightly darker blue */
    color: #ffffff;
}

/* คง Custom CSS อื่นๆ ของ Interactive Component ไว้ */
.card{ background:var(--card); border:1px solid var(--border); border-radius:16px; padding:16px; box-shadow:0 8px 24px rgba(0,0,0,.05); }
.section-title{ font-weight:800; color:var(--text); margin-bottom:8px; }
.text-element{ position:absolute; cursor:move; padding:4px 6px; border:2px dashed transparent; user-select:none; white-space:pre-wrap; z-index:10; }
.text-element:hover{ border-color: var(--accent); background: rgba(37,99,235,.08); }
.text-element.selected{ border-color: var(--accent); background: rgba(37,99,235,.12); }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 2. SESSION STATE & PAGE SWITCHING LOGIC (SPA Core)
# ------------------------------------------------------------
# 2.1 Initialize Session State
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'Edit' # Default page
if 'app_theme' not in st.session_state:
    st.session_state.app_theme = 'Default'

# 2.2 Reusable function to create SPA button
def nav_button(label, page_key, icon=""):
    is_active = st.session_state.current_page == page_key
    
    # ใช้ st.button และ Custom CSS เพื่อให้ดูดี
    css_class = "active-page" if is_active else ""
    
    if st.button(f"{icon} {label}", key=f"nav_{page_key}", use_container_width=True):
        st.session_state.current_page = page_key
        st.experimental_rerun() # บังคับให้ Streamlit Rerun เพื่อแสดงหน้าใหม่

    # Hack: Inject CSS class for active state AFTER button is rendered
    if is_active:
         st.markdown(f"""
             <script>
             const btn = document.querySelector('[data-testid="stSidebar"] button[key="nav_{page_key}"]');
             if(btn) btn.classList.add('{css_class}');
             </script>
         """, unsafe_allow_html=True)

# ------------------------------------------------------------
# 3. PAGE RENDER FUNCTIONS
# ------------------------------------------------------------

# 3.1 PDF Writer (Unchanged Logic)
def edit_pdf_with_elements(pdf_bytes: bytes, text_elements):
    # ... (Keep your existing edit_pdf_with_elements function logic here) ...
    # เนื่องจากโค้ดยาวมาก ขออนุญาตละไว้ในส่วนนี้ แต่ให้ใส่โค้ดเดิมของคุณลงไป

    """สร้าง PDF ใหม่โดยเพิ่ม text overlay (base coordinate: A4 portrait ~ 595x842 px)"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    width, height = A4 # 595.2755905511812, 841.8897637795277

    # group by page
    elements_by_page = {}
    for element in text_elements:
        page_idx = int(element.get('page', 1))
        elements_by_page.setdefault(page_idx, []).append(element)

    for page_num, page in enumerate(reader.pages, start=1):
        if page_num in elements_by_page:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=A4)

            for el in elements_by_page[page_num]:
                text = el.get('text', '')
                x = float(el.get('x', 50))
                y = float(el.get('y', 700))
                font_size = int(el.get('fontSize', 16))
                font_name = el.get('font', 'Helvetica')
                color = el.get('color', '#111111')
                
                # color hex -> rgb
                try:
                    c = color.lstrip('#'); r,g,b = (int(c[i:i+2],16)/255 for i in (0,2,4))
                except Exception:
                    r=g=b=0
                can.setFillColorRGB(r,g,b)

                try:
                    if font_name in ["THSarabunPSK", "THSarabunNew"] and FONTS_AVAILABLE:
                        fp = f"fonts/{font_name}.ttf"
                        if os.path.exists(fp):
                            pdfmetrics.registerFont(TTFont(font_name, fp))
                            can.setFont(font_name, font_size)
                        else:
                            can.setFont('Helvetica', font_size)
                    else:
                        can.setFont(font_name, font_size)
                except Exception:
                    can.setFont('Helvetica', font_size)

                # origin bottom-left
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


# 3.2 Interactive Editor Component (Unchanged Logic)
# เนื่องจากโค้ดยาวมาก ขออนุญาตละไว้ในส่วนนี้ แต่ให้ใส่โค้ดเดิมของคุณลงไป
def interactive_pdf_editor(pdf_bytes: bytes | None = None):
    # ... (Keep your existing interactive_pdf_editor function logic here) ...
    pdf_base64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

    # embed Thai fonts for browser preview (optional)
    custom_font_css = ""
    for fname in ["THSarabunPSK", "THSarabunNew"]:
        fpath = os.path.join("fonts", f"{fname}.ttf")
        if os.path.exists(fpath):
            try:
                with open(fpath, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                custom_font_css += f"""
                @font-face {{
                    font-family: '{fname}';
                    src: url(data:font/ttf;base64,{b64}) format('truetype');
                    font-weight: normal; font-style: normal; font-display: swap;
                }}
                """
            except Exception:
                pass

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
      <style>
        {custom_font_css}
      </style>
    </head>
    <body>
      <div class="card" style="margin-top:8px;">
        <div class="section-title">Interactive Editor</div>
        <div class="toolbar">
          <textarea id="textInput" placeholder="พิมพ์ข้อความที่ต้องการเพิ่ม..."></textarea>
          <select id="fontSelect">
            <option value="Helvetica">Helvetica</option>
            <option value="Times-Roman">Times New Roman</option>
            <option value="Courier">Courier</option>
            <option value="THSarabunPSK">TH Sarabun PSK</option>
            <option value="THSarabunNew">TH Sarabun New</option>
          </select>
          <input type="number" id="fontSize" value="16" min="8" max="72">
          <input type="color" id="textColor" value="#111111">
          <div class="zoom-controls">
            <button class="zoom-btn" id="zoomOut">−</button>
            <div class="zoom-value" id="zoomVal">125%</div>
            <button class="zoom-btn" id="zoomIn">+</button>
            <input type="range" id="zoomRange" min="50" max="200" step="5" value="125" style="width:160px;">
          </div>
        </div>

        <div class="canvas-wrap">
          <div class="viewport" id="viewport" style="width: 744px; height: 1053px;">
            <div id="page">
              <canvas id="pdfCanvas" width="595" height="842"></canvas>
            </div>
          </div>

          <div style="display:flex; gap:8px; margin-top:10px;">
            <button class="btn btn-ghost" id="addBtn">➕ เพิ่มข้อความ</button>
            <button class="btn btn-danger" id="clearBtn">🗑️ ล้างข้อความในหน้านี้</button>
          </div>
        </div>
      </div>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <script>
        // --- helpers ---
        const CSS_FONT_MAP = {{
          "Helvetica":"Helvetica, Arial, sans-serif",
          "Times-Roman":"'Times New Roman', Times, serif",
          "Courier":"'Courier New', Courier, monospace",
          "THSarabunPSK":"'THSarabunPSK','Sarabun','Noto Sans Thai',sans-serif",
          "THSarabunNew":"'THSarabunNew','Sarabun','Noto Sans Thai',sans-serif"
        }};
        function cssFontFamily(n){{ return CSS_FONT_MAP[n] || n; }}
        function base64ToUint8Array(b64){{ const r=atob(b64); const a=new Uint8Array(r.length); for(let i=0;i<r.length;i++) a[i]=r.charCodeAt(i); return a; }}

        // base page size in px (A4 @ ~72dpi)
        const BASE_W = 595, BASE_H = 842;

        // state
        let textElements = [];
        let elementCounter = 0;
        let selectedElement = null, isDragging=false, isResizing=false, startX, startY, startLeft, startTop, startFontSize;
        let currentZoom = 1.25; // default 125%

        // DOM
        const page   = document.getElementById('page');
        const view   = document.getElementById('viewport');
        const canvas = document.getElementById('pdfCanvas');
        const ctx    = canvas.getContext('2d');

        // zoom controls
        const zoomRange = document.getElementById('zoomRange');
        const zoomIn    = document.getElementById('zoomIn');
        const zoomOut   = document.getElementById('zoomOut');
        const zoomVal   = document.getElementById('zoomVal');
        function applyZoom(){
          page.style.transform = 'scale(' + currentZoom + ')';
          view.style.width  = (BASE_W * currentZoom + 150) + 'px';  // give some space
          view.style.height = (BASE_H * currentZoom + 150) + 'px';
          zoomVal.textContent = Math.round(currentZoom*100) + '%';
        }
        function setZoomFromRange(v){ currentZoom = parseInt(v,10)/100; applyZoom(); }
        zoomRange.addEventListener('input', e=> setZoomFromRange(e.target.value));
        zoomIn.addEventListener('click', ()=>{ let v = Math.min(200, parseInt(zoomRange.value,10)+10); zoomRange.value=v; setZoomFromRange(v); });
        zoomOut.addEventListener('click', ()=>{ let v = Math.max(50,  parseInt(zoomRange.value,10)-10); zoomRange.value=v; setZoomFromRange(v); });
        applyZoom();

        // load PDF page 1
        const pdfData = '{pdf_base64}';
        if(pdfData){
          pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
          const uint8 = base64ToUint8Array(pdfData);
          pdfjsLib.getDocument({data:uint8}).promise.then(pdf => pdf.getPage(1)).then(pagePDF=>{
            const unscaled = pagePDF.getViewport({scale:1});
            const scale = Math.min(BASE_W/unscaled.width, BASE_H/unscaled.height);
            const viewport = pagePDF.getViewport({scale});
            canvas.width = viewport.width; canvas.height = viewport.height;
            return pagePDF.render({canvasContext:ctx, viewport}).promise;
          }).catch(err=>console.error('pdf.js error', err));
        }

        // --- editor interactions ---
        document.getElementById('addBtn').addEventListener('click', addText);
        document.getElementById('clearBtn').addEventListener('click', clearAll);

        function addText(){
          const t = document.getElementById('textInput').value.trim();
          if(!t){ alert('กรุณาใส่ข้อความ'); return; }
          const el = {{
            id: ++elementCounter, text: t, x: 50, y: 50,
            fontSize: parseInt(document.getElementById('fontSize').value)||16,
            font: document.getElementById('fontSelect').value,
            color: document.getElementById('textColor').value,
            page: 1
          }};
          textElements.push(el); createTextDiv(el); document.getElementById('textInput').value='';
          postElements();
        }

        function createTextDiv(el){
          const div = document.createElement('div');
          div.className = 'text-element'; div.id = 'text-'+el.id;
          Object.assign(div.style, {{ left:el.x+'px', top:el.y+'px',
            fontSize:el.fontSize+'px', fontFamily:cssFontFamily(el.font), color:el.color }});
          div.textContent = el.text;

          const del = document.createElement('button');
          del.className='delete-btn'; del.textContent='×';
          del.onclick = (e)=>{ e.stopPropagation(); deleteText(el.id); };
          const rh  = document.createElement('div'); rh.className='resize-handle';

          div.appendChild(del); div.appendChild(rh);
          page.appendChild(div);

          // drag/resize
          div.addEventListener('mousedown', e=> startDrag(e, el));
          rh.addEventListener('mousedown', e=> startResize(e, el));
        }

        function startDrag(e, el){
          if(e.target.className==='resize-handle') return;
          selectedElement=el; isDragging=true; startX=e.clientX; startY=e.clientY; startLeft=el.x; startTop=el.y;
          document.getElementById('text-'+el.id).classList.add('selected');
        }
        function startResize(e, el){
          e.stopPropagation(); selectedElement=el; isResizing=true; startY=e.clientY; startFontSize=el.fontSize;
        }

        document.addEventListener('mousemove', e=>{
          if(isDragging && selectedElement){
            const dx=(e.clientX-startX)/currentZoom, dy=(e.clientY-startY)/currentZoom;
            selectedElement.x=Math.max(0, Math.min(startLeft+dx, BASE_W-4));
            selectedElement.y=Math.max(0, Math.min(startTop+dy,  BASE_H-4));
            const div=document.getElementById('text-'+selectedElement.id);
            div.style.left=selectedElement.x+'px'; div.style.top=selectedElement.y+'px';
          }
          if(isResizing && selectedElement){
            const dy=(e.clientY-startY)/currentZoom;
            const s=Math.max(8, Math.min(72, startFontSize+dy));
            selectedElement.fontSize=s; document.getElementById('text-'+selectedElement.id).style.fontSize=s+'px';
          }
        });

        document.addEventListener('mouseup', ()=>{
          if(selectedElement){
            document.getElementById('text-'+selectedElement.id).classList.remove('selected');
          }
          const changed = isDragging || isResizing;
          isDragging=false; isResizing=false; selectedElement=null;
          if(changed) postElements(); // ส่งข้อมูลทุกครั้งหลังปล่อยเมาส์
        });

        function deleteText(id){
          textElements = textElements.filter(x=>x.id!==id);
          const div=document.getElementById('text-'+id); if(div) div.remove();
          postElements();
        }
        function clearAll(){
          if(!confirm('ลบข้อความทั้งหมดบนหน้านี้?')) return;
          textElements.forEach(x=>{ const d=document.getElementById('text-'+x.id); if(d) d.remove(); });
          textElements=[]; postElements();
        }

        // realtime style changes on selected element
        document.getElementById('fontSelect').addEventListener('change', e=>{
          if(!selectedElement) return; selectedElement.font=e.target.value;
          document.getElementById('text-'+selectedElement.id).style.fontFamily = cssFontFamily(selectedElement.font);
          postElements();
        });
        document.getElementById('fontSize').addEventListener('change', e=>{
          if(!selectedElement) return; const s=parseInt(e.target.value)||16;
          selectedElement.fontSize=s; document.getElementById('text-'+selectedElement.id).style.fontSize=s+'px';
          postElements();
        });
        document.getElementById('textColor').addEventListener('change', e=>{
          if(!selectedElement) return; selectedElement.color=e.target.value;
          document.getElementById('text-'+selectedElement.id).style.color=selectedElement.color;
          postElements();
        });

        // send elements to Streamlit (no save button; auto)
        function postElements(){
          const payload = JSON.stringify(textElements);
          const msg = { isStreamlitMessage: true, type: "streamlit:setComponentValue", value: payload };
          window.parent.postMessage(msg, "*");
        }

        // initialize with empty
        postElements();
      </script>
    </body>
    </html>
    """
    
    # ใช้ .format() เพื่อแทรกตัวแปร Python
    html = html_template.format(
        pdf_base64=pdf_base64, 
        custom_font_css=custom_font_css
    )
    
    return components.html(html, height=900, scrolling=True)

# 3.3 Interactive Editor Page
def render_editor_page():
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="edit_pdf")

    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        st.success(f"✅ อัปโหลดไฟล์สำเร็จ: {uploaded_file.name}")
        st.info(f"📄 ไฟล์มี {total_pages} หน้า (ตัวอย่างจะแก้ไขบนหน้าแรก)")

        st.markdown('<div class="sticky-actions"><div class="action-bar">\
            <div>เคลื่อนย้าย/ปรับขนาดข้อความ แล้วปล่อยเมาส์ ระบบจะสร้างไฟล์ใหม่ให้อัตโนมัติ</div>\
            <div></div></div></div>', unsafe_allow_html=True)

        # Component returns JSON string (elements) every time user changes
        elements_json = interactive_pdf_editor(pdf_bytes)

        # Keep elements in session & auto build
        elements = []
        if elements_json:
            try:
                elements = json.loads(elements_json) or []
                st.session_state.text_elements = elements
            except Exception:
                elements = st.session_state.get('text_elements', [])
        else:
            elements = st.session_state.get('text_elements', [])

        # Auto-generate PDF when elements available (no extra button)
        col1, col2 = st.columns([3,2])
        with col2:
            st.markdown("#### 📤 ไฟล์ผลลัพธ์")
            try:
                edited_pdf = edit_pdf_with_elements(pdf_bytes, elements)
                st.success("ไฟล์อัปเดตแล้ว")
                st.download_button(
                    label="📥 ดาวน์โหลด PDF ที่แก้ไขแล้ว",
                    data=edited_pdf,
                    file_name="edited_" + uploaded_file.name,
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดระหว่างสร้างไฟล์: {e}")

        with col1:
            st.markdown("#### 🧾 รายการข้อความ")
            if elements:
                for i, el in enumerate(elements, 1):
                    st.write(f"**{i}.** `{el.get('text','')[:60]}` | ฟอนต์: {el.get('font')} | ขนาด: {el.get('fontSize')} | ตำแหน่ง: ({el.get('x')}, {el.get('y')})")
                with st.expander("ดูข้อมูล JSON"):
                    st.json(elements)
            else:
                st.info("ยังไม่มีข้อความบนหน้าเอกสาร")

# 3.4 Merge PDFs Page
def render_merger_page():
    st.markdown('<div class="card"><div class="section-title">🔗 รวมหลายไฟล์ PDF</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ PDF (หลายไฟล์)", type="pdf", accept_multiple_files=True, key="merge_files")
    if uploaded_files and len(uploaded_files) > 1:
        st.info(f"เลือก {len(uploaded_files)} ไฟล์")
        if st.button("รวมไฟล์", type="primary", use_container_width=True):
            with st.spinner("กำลังรวมไฟล์..."):
                merger = PdfMerger()
                for pdf in uploaded_files:
                    merger.append(io.BytesIO(pdf.getvalue()))
                output = io.BytesIO()
                merger.write(output)
                merger.close()
                output.seek(0)
                st.success("✅ รวมไฟล์สำเร็จ!")
                st.download_button("📥 ดาวน์โหลดไฟล์ที่รวมแล้ว", data=output, file_name="merged.pdf", mime="application/pdf", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 3.5 Settings Page
def render_settings_page():
    st.title("⚙️ ตั้งค่าแอปพลิเคชัน")
    st.markdown("ส่วนนี้ใช้สำหรับการตั้งค่าทั่วไปของแอปพลิเคชัน")
    
    st.subheader("การตั้งค่าธีม")
    
    # ใช้วิธีเปลี่ยน Session State โดยตรงเพื่อเรียก Rerun
    new_theme = st.selectbox(
        "เลือกธีม", 
        ["Default", "Dark Mode (Requires Rerun)"],
        index=0 if st.session_state.app_theme == 'Default' else 1,
        key="theme_selector"
    )
    
    # Check if theme changed
    if new_theme != st.session_state.app_theme:
        st.session_state.app_theme = new_theme
        st.warning("การเปลี่ยนธีมอาจต้อง Rerun หน้าทั้งหมด")
        if st.button("บันทึกและเปลี่ยนธีม"):
            # ในแอปจริง, คุณจะต้องแก้ไข CSS ในส่วน <style> ให้รองรับธีม Dark Mode
            st.success(f"เปลี่ยนธีมเป็น {new_theme} แล้ว! (ต้องมีการปรับปรุงโค้ด CSS เพิ่มเติม)")
            st.experimental_rerun()
            
    st.subheader("ข้อมูลเวอร์ชัน")
    st.code("Version: 1.0.0 (SPA Beta)")

# ------------------------------------------------------------
# 4. APP SHELL & MAIN RENDER
# ------------------------------------------------------------

# 4.1 Header
st.markdown('<div class="header-card"><h1>📄 PDF Manager Pro — Interactive Edition</h1><p>เครื่องมือจัดการไฟล์ PDF แบบ Single Page Application (SPA)</p></div>', unsafe_allow_html=True)

# 4.2 Sidebar Navigation (SPA Menu)
with st.sidebar:
    st.header("ฟังก์ชันหลัก")
    nav_button("✏️ แก้ไข PDF (Interactive)", 'Edit', icon="✏️")
    nav_button("🔗 รวมไฟล์ PDF", 'Merge', icon="🔗")
    st.markdown("---")
    st.header("ตั้งค่า")
    nav_button("⚙️ ตั้งค่าแอป", 'Settings', icon="⚙️")
    
# 4.3 Main Content Router (The "Single Page" Switch)
if st.session_state.current_page == 'Edit':
    render_editor_page()
elif st.session_state.current_page == 'Merge':
    render_merger_page()
elif st.session_state.current_page == 'Settings':
    render_settings_page()

# 4.4 Footer
st.markdown("""
<hr style="margin:28px 0; opacity:.2">
<div style='text-align:center; color:#64748b'>
    © 2025 PDF Manager Pro – สร้างด้วย Streamlit
</div>
""", unsafe_allow_html=True)
