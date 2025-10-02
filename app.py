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

# Custom CSS (modern neutral theme; hide hamburger & footer)
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

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
    font-family: 'Sarabun', 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}
.block-container { padding-top: 14px; }

.header-card{
    background: var(--card); color: var(--text);
    border: 1px solid var(--border);
    border-radius: 16px; padding: 18px 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,.06);
}
.header-card h1{ margin:0; font-size:1.35rem; font-weight:800; letter-spacing:.2px; }
.header-card p{ margin:6px 0 0; color:var(--muted); }

/* Sidebar SPA buttons */
div[data-testid="stSidebar"] button {
    border: none; background: transparent; color: var(--text);
    padding: 10px 16px; margin: 4px 0; width: 100%;
    text-align: left; border-radius: 8px; font-weight: 600;
}
div[data-testid="stSidebar"] button:hover {
    background: #eef1f6; color: var(--accent);
}
div[data-testid="stSidebar"] button.active-page {
    background: var(--accent); color: #ffffff;
}
div[data-testid="stSidebar"] button.active-page:hover {
    background: #1e40af; color: #ffffff;
}

.card{ background:var(--card); border:1px solid var(--border); border-radius:16px; padding:16px; box-shadow:0 8px 24px rgba(0,0,0,.05); }
.section-title{ font-weight:800; color:var(--text); margin-bottom:8px; }

.text-element{
    position:absolute; cursor:move; padding:4px 6px;
    border:2px dashed transparent; user-select:none; white-space:pre-wrap; z-index:10;
}
.text-element:hover{ border-color: var(--accent); background: rgba(37,99,235,.08); }
.text-element.selected{ border-color: var(--accent); background: rgba(37,99,235,.12); }

.toolbar{
    display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:8px;
}
.toolbar textarea{ width:260px; height:40px; padding:8px; border-radius:8px; border:1px solid var(--border); }
.toolbar select, .toolbar input[type="number"], .toolbar input[type="color"]{
    padding:6px 8px; border-radius:8px; border:1px solid var(--border);
}
.zoom-controls{ display:flex; align-items:center; gap:8px; margin-left:auto; }
.zoom-btn{ padding:6px 10px; border:1px solid var(--border); background:#fff; border-radius:8px; cursor:pointer; }
.zoom-value{ min-width:54px; text-align:center; color:var(--muted); }

.canvas-wrap{ display:flex; flex-direction:column; }
.viewport{
    background:#fff; border:1px solid var(--border); border-radius:12px;
    overflow:auto; display:flex; justify-content:center; align-items:center;
    box-shadow:0 6px 20px rgba(0,0,0,.06); margin-top:6px;
}
#page{ position:relative; transform-origin: top left; }

.btn{ padding:8px 12px; border-radius:10px; border:1px solid var(--border); background:#fff; cursor:pointer; }
.btn-ghost{ background:#fff; }
.btn-danger{ background:#fff0f0; border-color:#fbcaca; color:#b91c1c; }
.btn:active{ transform: translateY(1px); }

.delete-btn{
    position:absolute; right:-10px; top:-10px; width:22px; height:22px;
    border:none; border-radius:50%; background:#ef4444; color:#fff; cursor:pointer;
    display:flex; align-items:center; justify-content:center; font-weight:700;
}
.resize-handle{
    position:absolute; right:-6px; bottom:-6px; width:12px; height:12px;
    background:#2563eb; border-radius:2px; cursor:nwse-resize;
}
.pagebar{
    display:flex; gap:8px; align-items:center; margin:8px 0 0; flex-wrap:wrap;
}
.pagebar button{ padding:6px 10px; border-radius:8px; border:1px solid var(--border); background:#fff; cursor:pointer; }
.pagebar select{ padding:6px 10px; border-radius:8px; border:1px solid var(--border); }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 2. SESSION STATE & PAGE SWITCHING LOGIC (SPA Core)
# ------------------------------------------------------------
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'Edit' # Default page
if 'app_theme' not in st.session_state:
    st.session_state.app_theme = 'Default'

def nav_button(label, page_key, icon=""):
    is_active = st.session_state.current_page == page_key
    css_class = "active-page" if is_active else ""
    if st.button(f"{icon} {label}", key=f"nav_{page_key}", use_container_width=True):
        st.session_state.current_page = page_key
        st.experimental_rerun()
    if is_active:
        st.markdown(f"""
            <script>
            const root = window.parent?.document || document;
            const btns = root.querySelectorAll('[data-testid="stSidebar"] button');
            if(btns) {{
              btns.forEach(b => {{
                if (b.innerText.trim() === "{icon} {label}".trim()) b.classList.add("{css_class}");
              }});
            }}
            </script>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# 3. PAGE RENDER FUNCTIONS
# ------------------------------------------------------------

# 3.1 PDF Writer (unchanged logic; already grouped by page)
def edit_pdf_with_elements(pdf_bytes: bytes, text_elements):
    """สร้าง PDF ใหม่โดยเพิ่ม text overlay (base coordinate: A4 portrait ~ 595x842 px)"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    width, height = A4  # ~595x842 (points)

    # group by page
    elements_by_page = {}
    for element in text_elements or []:
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
                    c = color.lstrip('#')
                    r, g, b = (int(c[i:i+2], 16) / 255 for i in (0, 2, 4))
                except Exception:
                    r = g = b = 0
                can.setFillColorRGB(r, g, b)

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

# 3.2 Interactive Editor Component
def interactive_pdf_editor(pdf_bytes: bytes | None = None, total_pages: int = 1):
    pdf_base64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

    # embed Thai fonts for browser preview (optional)
    custom_font_css = ""
    for fname in ["THSarabunPSK", "THSarabunNew"]:
        fpath = os.path.join("fonts", f"{fname}.ttf")
        if os.path.exists(fpath):
            try:
                with open(fpath, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                custom_font_css += """
                @font-face {{
                    font-family: '{fname}';
                    src: url(data:font/ttf;base64,{b64}) format('truetype');
                    font-weight: normal; font-style: normal; font-display: swap;
                }}
                """.format(fname=fname, b64=b64)
            except Exception:
                pass

    # IMPORTANT: use normal triple-quoted string (NOT f-string) and escape braces with {{ }}
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
      <style>
        {custom_font_css}
        body{{ margin:0; padding:0; }}
      </style>
    </head>
    <body>
      <div class="card" style="margin-top:8px;">
        <div class="section-title">Interactive Editor</div>

        <!-- PAGE BAR -->
        <div class="pagebar">
          <button id="prevPage">◀</button>
          <select id="pageSelect"></select>
          <button id="nextPage">▶</button>
          <span style="color:#64748b;">Total: <strong id="totalPages">{total_pages}</strong> pages</span>
        </div>

        <!-- TOOLBAR -->
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
            <input type="range" id="zoomRange" min="50" max="240" step="5" value="125" style="width:180px;">
          </div>
        </div>

        <!-- CANVAS -->
        <div class="canvas-wrap">
          <div class="viewport" id="viewport" style="width: 870px; height: 1200px;">
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
        let textElements = [];        // all pages
        let elementCounter = 0;
        let selectedElement = null, isDragging=false, isResizing=false, startX, startY, startLeft, startTop, startFontSize;
        let currentZoom = 1.25; // default 125%
        let currentPage = 1;
        const TOTAL_PAGES = parseInt(document.getElementById('totalPages').textContent, 10) || 1;

        // DOM
        const page   = document.getElementById('page');
        const view   = document.getElementById('viewport');
        const canvas = document.getElementById('pdfCanvas');
        const ctx    = canvas.getContext('2d');
        const pageSelect = document.getElementById('pageSelect');

        const zoomRange = document.getElementById('zoomRange');
        const zoomIn    = document.getElementById('zoomIn');
        const zoomOut   = document.getElementById('zoomOut');
        const zoomVal   = document.getElementById('zoomVal');

        // fill page select
        for(let i=1;i<=TOTAL_PAGES;i++) {{
          const opt = document.createElement('option'); opt.value = i; opt.textContent = 'Page ' + i;
          pageSelect.appendChild(opt);
        }}
        pageSelect.value = 1;

        function applyZoom(){{
          page.style.transform = 'scale(' + currentZoom + ')';
          view.style.width  = (BASE_W * currentZoom + 180) + 'px';
          view.style.height = (BASE_H * currentZoom + 180) + 'px';
          zoomVal.textContent = Math.round(currentZoom*100) + '%';
        }}
        function setZoomFromRange(v){{ currentZoom = parseInt(v,10)/100; applyZoom(); }}
        zoomRange.addEventListener('input', e=> setZoomFromRange(e.target.value));
        zoomIn.addEventListener('click', ()=>{{ let v = Math.min(240, parseInt(zoomRange.value,10)+10); zoomRange.value=v; setZoomFromRange(v); }});
        zoomOut.addEventListener('click', ()=>{{ let v = Math.max(50,  parseInt(zoomRange.value,10)-10); zoomRange.value=v; setZoomFromRange(v); }});
        applyZoom();

        // load PDF
        const pdfData = '{pdf_base64}';
        let pdfDoc = null;
        let pageViewportScale = 1;

        function renderPage(n){{
          if(!pdfDoc) return;
          currentPage = n;
          pageSelect.value = n;

          pdfDoc.getPage(n).then(pagePDF => {{
            const unscaled = pagePDF.getViewport({{scale:1}});
            const scale = Math.min(BASE_W/unscaled.width, BASE_H/unscaled.height);
            const viewport = pagePDF.getViewport({{scale}});
            pageViewportScale = scale;
            canvas.width = viewport.width; canvas.height = viewport.height;
            return pagePDF.render({{canvasContext:ctx, viewport}}).promise;
          }}).then(()=>{{
            // clear existing DOM text elements and re-draw only current page's
            const nodes = Array.from(document.querySelectorAll('.text-element'));
            nodes.forEach(n => n.remove());
            textElements.filter(e => e.page === currentPage).forEach(createTextDiv);
          }}).catch(err=>console.error('render error', err));
        }}

        if(pdfData){{
          pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
          const uint8 = base64ToUint8Array(pdfData);
          pdfjsLib.getDocument({{data:uint8}}).promise.then(pdf => {{
            pdfDoc = pdf;
            renderPage(1);
          }}).catch(err=>console.error('pdf.js error', err));
        }}

        // page navigation
        document.getElementById('prevPage').addEventListener('click', ()=> {{
          if(currentPage > 1) renderPage(currentPage-1);
        }});
        document.getElementById('nextPage').addEventListener('click', ()=> {{
          if(currentPage < TOTAL_PAGES) renderPage(currentPage+1);
        }});
        pageSelect.addEventListener('change', e=> {{
          const n = parseInt(e.target.value,10)||1;
          renderPage(Math.min(Math.max(n,1), TOTAL_PAGES));
        }});

        // --- editor interactions ---
        document.getElementById('addBtn').addEventListener('click', addText);
        document.getElementById('clearBtn').addEventListener('click', clearAllOnThisPage);

        function addText(){{
          const t = document.getElementById('textInput').value.trim();
          if(!t){{ alert('กรุณาใส่ข้อความ'); return; }}
          const el = {{
            id: ++elementCounter, text: t, x: 50, y: 50,
            fontSize: parseInt(document.getElementById('fontSize').value)||16,
            font: document.getElementById('fontSelect').value,
            color: document.getElementById('textColor').value,
            page: currentPage
          }};
          textElements.push(el); createTextDiv(el);
          document.getElementById('textInput').value='';
          postElements();
        }}

        function createTextDiv(el){{
          const div = document.createElement('div');
          div.className = 'text-element'; div.id = 'text-'+el.id;
          Object.assign(div.style, {{
            left:el.x+'px', top:el.y+'px',
            fontSize:el.fontSize+'px', fontFamily:cssFontFamily(el.font), color:el.color
          }});
          div.textContent = el.text;

          const del = document.createElement('button'); del.className='delete-btn'; del.textContent='×';
          del.onclick = (e)=>{{ e.stopPropagation(); deleteText(el.id); }};
          const rh  = document.createElement('div'); rh.className='resize-handle';

          div.appendChild(del); div.appendChild(rh);
          page.appendChild(div);

          // drag/resize
          div.addEventListener('mousedown', e=> startDrag(e, el));
          rh.addEventListener('mousedown', e=> startResize(e, el));
        }}

        function startDrag(e, el){{
          if(e.target.className==='resize-handle') return;
          selectedElement=el; isDragging=true; startX=e.clientX; startY=e.clientY; startLeft=el.x; startTop=el.y;
          document.getElementById('text-'+el.id).classList.add('selected');
        }}
        function startResize(e, el){{
          e.stopPropagation(); selectedElement=el; isResizing=true; startY=e.clientY; startFontSize=el.fontSize;
        }}

        document.addEventListener('mousemove', e=>{{
          if(isDragging && selectedElement){{
            const dx=(e.clientX-startX)/currentZoom, dy=(e.clientY-startY)/currentZoom;
            selectedElement.x=Math.max(0, Math.min(startLeft+dx, BASE_W-4));
            selectedElement.y=Math.max(0, Math.min(startTop+dy,  BASE_H-4));
            const div=document.getElementById('text-'+selectedElement.id);
            div.style.left=selectedElement.x+'px'; div.style.top=selectedElement.y+'px';
          }}
          if(isResizing && selectedElement){{
            const dy=(e.clientY-startY)/currentZoom;
            const s=Math.max(8, Math.min(72, startFontSize+dy));
            selectedElement.fontSize=s; document.getElementById('text-'+selectedElement.id).style.fontSize=s+'px';
          }}
        }});

        document.addEventListener('mouseup', ()=>{{
          if(selectedElement){{
            const d=document.getElementById('text-'+selectedElement.id);
            if(d) d.classList.remove('selected');
          }}
          const changed = isDragging || isResizing;
          isDragging=false; isResizing=false; selectedElement=null;
          if(changed) postElements(); // ส่งข้อมูลทุกครั้งหลังปล่อยเมาส์
        }});

        function deleteText(id){{
          const found = textElements.find(x=>x.id===id);
          textElements = textElements.filter(x=>x.id!==id);
          const div=document.getElementById('text-'+id); if(div) div.remove();
          if(found) postElements();
        }}

        function clearAllOnThisPage(){{
          if(!confirm('ลบข้อความทั้งหมดในหน้านี้?')) return;
          const keep = [];
          for(const x of textElements){{
            if(x.page !== currentPage) keep.push(x);
          }}
          // remove DOM nodes
          const list = Array.from(document.querySelectorAll('.text-element'));
          list.forEach(n => n.remove());
          textElements = keep;
          postElements();
        }}

        // realtime style changes on selected element
        document.getElementById('fontSelect').addEventListener('change', e=>{{
          if(!selectedElement) return; selectedElement.font=e.target.value;
          const n=document.getElementById('text-'+selectedElement.id);
          if(n) n.style.fontFamily = cssFontFamily(selectedElement.font);
          postElements();
        }});
        document.getElementById('fontSize').addEventListener('change', e=>{{
          if(!selectedElement) return; const s=parseInt(e.target.value)||16;
          selectedElement.fontSize=s;
          const n=document.getElementById('text-'+selectedElement.id);
          if(n) n.style.fontSize=s+'px';
          postElements();
        }});
        document.getElementById('textColor').addEventListener('change', e=>{{
          if(!selectedElement) return; selectedElement.color=e.target.value;
          const n=document.getElementById('text-'+selectedElement.id);
          if(n) n.style.color=selectedElement.color;
          postElements();
        }});

        // send elements to Streamlit (auto; no save button)
        function postElements(){{
          const payload = JSON.stringify(textElements);
          const msg = {{ isStreamlitMessage: true, type: "streamlit:setComponentValue", value: payload }};
          window.parent.postMessage(msg, "*");
        }}

        // initialize with empty (ensures Streamlit has a value)
        postElements();
      </script>
    </body>
    </html>
    """

    html = html_template.format(
        pdf_base64=pdf_base64,
        custom_font_css=custom_font_css,
        total_pages=total_pages
    )

    return components.html(html, height=980, scrolling=True)

# 3.3 Interactive Editor Page
def render_editor_page():
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="edit_pdf")

    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        st.success(f"✅ อัปโหลดไฟล์สำเร็จ: {uploaded_file.name}")
        st.info(f"📄 ไฟล์มี {total_pages} หน้า — ใช้ตัวเลือก Page ด้านบนของตัวแก้ไขเพื่อสลับหน้าได้")

        st.markdown(
            '<div class="card"><div><strong>วิธีใช้:</strong> ลาก/ปรับขนาดข้อความ ปล่อยเมาส์แล้วระบบจะสร้างไฟล์ใหม่ให้อัตโนมัติ (ไม่ต้องกดบันทึก)</div></div>',
            unsafe_allow_html=True
        )

        # Component returns JSON string (elements) every time user changes
        elements_json = interactive_pdf_editor(pdf_bytes, total_pages)

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
            st.markdown("#### 🧾 รายการข้อความทั้งหมด")
            if elements:
                for i, el in enumerate(elements, 1):
                    st.write(
                        f"**{i}.** Page {el.get('page',1)} | "
                        f"`{str(el.get('text',''))[:60]}` | "
                        f"ฟอนต์: {el.get('font')} | ขนาด: {el.get('fontSize')} | "
                        f"ตำแหน่ง: ({el.get('x')}, {el.get('y')})"
                    )
                with st.expander("ดูข้อมูล JSON"):
                    st.json(elements)
            else:
                st.info("ยังไม่มีข้อความบนเอกสาร")

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
    new_theme = st.selectbox(
        "เลือกธีม",
        ["Default", "Dark Mode (Requires Rerun)"],
        index=0 if st.session_state.app_theme == 'Default' else 1,
        key="theme_selector"
    )
    if new_theme != st.session_state.app_theme:
        st.session_state.app_theme = new_theme
        st.warning("การเปลี่ยนธีมอาจต้อง Rerun หน้าทั้งหมด")
        if st.button("บันทึกและเปลี่ยนธีม"):
            st.success(f"เปลี่ยนธีมเป็น {new_theme} แล้ว! (ต้องแก้ CSS เพิ่มเติม)")
            st.experimental_rerun()

    st.subheader("ข้อมูลเวอร์ชัน")
    st.code("Version: 1.0.1 (SPA Beta, multi-page + zoom fix)")

# ------------------------------------------------------------
# 4. APP SHELL & MAIN RENDER
# ------------------------------------------------------------

st.markdown('<div class="header-card"><h1>📄 PDF Manager Pro — Interactive Edition</h1><p>เครื่องมือจัดการไฟล์ PDF แบบ Single Page Application (SPA)</p></div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("ฟังก์ชันหลัก")
    nav_button("✏️ แก้ไข PDF (Interactive)", 'Edit', icon="✏️")
    nav_button("🔗 รวมไฟล์ PDF", 'Merge', icon="🔗")
    st.markdown("---")
    st.header("ตั้งค่า")
    nav_button("⚙️ ตั้งค่าแอป", 'Settings', icon="⚙️")

if st.session_state.current_page == 'Edit':
    render_editor_page()
elif st.session_state.current_page == 'Merge':
    render_merger_page()
elif st.session_state.current_page == 'Settings':
    render_settings_page()

st.markdown("""
<hr style="margin:28px 0; opacity:.2">
<div style='text-align:center; color:#64748b'>
    © 2025 PDF Manager Pro – สร้างด้วย Streamlit
</div>
""", unsafe_allow_html=True)
