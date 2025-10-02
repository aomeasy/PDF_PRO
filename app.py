# app.py
import streamlit as st
import streamlit.components.v1 as components
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io, json, base64, os

# ----------------------------
# 1) Setup & Fonts
# ----------------------------
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase import ttfonts
    FONTS_AVAILABLE = True
except Exception:
    FONTS_AVAILABLE = False

st.set_page_config(
    page_title="PDF Manager Pro — Fullscreen",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------
# 2) Global Styles (modern)
# ----------------------------
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
:root{
  --bg:#f3f4f6; --surface:#ffffff; --border:#e5e7eb;
  --text:#0f172a; --muted:#6b7280; --accent:#2563eb;
  --danger:#ef4444; --success:#10b981;
}
html, body { background:var(--bg); font-family:'Sarabun','Inter',system-ui; }
.block-container { padding-top: 12px; }

.header-card{
  background:var(--surface); border:1px solid var(--border);
  border-radius:16px; padding:16px 18px; box-shadow:0 8px 24px rgba(0,0,0,.06);
}
.header-card h1{ margin:0; font-size:1.35rem; font-weight:800; color:var(--text); }
.header-card p{ margin:.25rem 0 0; color:var(--muted); }

/* Sidebar SPA buttons */
div[data-testid="stSidebar"] button{
  border:none; background:transparent; color:var(--text);
  padding:10px 14px; width:100%; text-align:left; border-radius:10px; font-weight:600;
}
div[data-testid="stSidebar"] button:hover{ background:#eef2ff; color:#1d4ed8; }
div[data-testid="stSidebar"] button.active-page{ background:#2563eb; color:#fff; }

/* Generic buttons */
.btn{ padding:8px 12px; border-radius:10px; border:1px solid var(--border); background:#fff; cursor:pointer; }
.btn:hover{ box-shadow:0 2px 8px rgba(0,0,0,.08); }

/* Fullscreen Editor Layout */
.editor-shell{
  display:grid; grid-template-columns: 240px 1fr 320px; gap:12px; height:calc(100vh - 210px);
}
.panel{
  background:var(--surface); border:1px solid var(--border); border-radius:14px;
  box-shadow:0 8px 24px rgba(0,0,0,.05); overflow:hidden;
}
.panel-header{
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 12px; border-bottom:1px solid var(--border);
  background:#fafafa; color:var(--text); font-weight:700;
}
.panel-body{ height:100%; overflow:auto; }

/* Thumbnails */
.thumb{ padding:8px; border-bottom:1px dashed var(--border); cursor:pointer; }
.thumb canvas{ width:100%; border:1px solid var(--border); border-radius:8px; background:#fff; }
.thumb.active{ background:#eef2ff; }

/* Center viewer */
.viewer-wrap{ height:100%; display:flex; flex-direction:column; }
.toolbar{
  display:flex; gap:10px; align-items:center; padding:8px 10px; border-bottom:1px solid var(--border); background:#fafafa;
}
.toolbar .group{ display:flex; gap:8px; align-items:center; }
.toolbar .seg{ display:flex; gap:0; border:1px solid var(--border); border-radius:10px; overflow:hidden; }
.toolbar .seg button{
  padding:8px 12px; border:none; background:#fff; cursor:pointer;
}
.toolbar .seg button:hover{ background:#f3f4f6; }

.viewer{
  position:relative; flex:1 1 auto; overflow:auto; background:#e5e7eb;
  display:flex; align-items:flex-start; justify-content:center;
}
.page-holder{
  position:relative; margin:24px; background:#fff; border:1px solid var(--border); border-radius:12px;
  box-shadow:0 10px 30px rgba(0,0,0,.08);
  transform-origin: top left;
}

/* Canvas and overlay */
.pdf-canvas{ position:relative; z-index:1; pointer-events:none; display:block; }
.text-layer{ position:absolute; left:0; top:0; width:100%; height:100%; z-index:10; }
.text-element{
  position:absolute; cursor:move; padding:2px 4px; border:2px dashed transparent;
  user-select:none; white-space:pre-wrap; background:transparent;
}
.text-element:hover{ border-color:#93c5fd; background:rgba(59,130,246,.06); }
.text-element.selected{ border-color:#2563eb; background:rgba(37,99,235,.12); }
.delete-btn{
  position:absolute; right:-10px; top:-10px; width:22px; height:22px; border:none; border-radius:50%;
  background:var(--danger); color:#fff; font-weight:800; cursor:pointer;
}
.resize-handle{
  position:absolute; right:-6px; bottom:-6px; width:12px; height:12px; background:#2563eb; border-radius:2px; cursor:nwse-resize;
}

/* Right props */
.props-body{ padding:10px; display:flex; flex-direction:column; gap:10px; }
.props-body input, .props-body select, .props-body textarea{
  width:100%; padding:8px 10px; border:1px solid var(--border); border-radius:10px; background:#fff;
}
.props-body label{ font-size:.9rem; color:var(--muted); }
.props-body .row{ display:grid; grid-template-columns: 1fr 1fr; gap:8px; }

/* Info chip */
.info-chip{ display:inline-flex; gap:6px; align-items:center; padding:6px 10px; border:1px solid var(--border); border-radius:999px; background:#fff; color:var(--muted); }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# 3) SPA nav helper
# ----------------------------
if 'current_page' not in st.session_state: st.session_state.current_page = 'Edit'
if 'app_theme' not in st.session_state: st.session_state.app_theme = 'Default'

def nav_button(label, page_key, icon=""):
    is_active = st.session_state.current_page == page_key
    if st.button(f"{icon} {label}", key=f"nav_{page_key}", use_container_width=True):
        st.session_state.current_page = page_key
        st.rerun()  # <- แทน experimental_rerun
    if is_active:
        st.markdown(f"""
          <script>
            const root = window.parent?.document || document;
            const btns = root.querySelectorAll('[data-testid="stSidebar"] button');
            btns?.forEach(b => {{ if (b.innerText.trim() === "{icon} {label}".trim()) b.classList.add("active-page"); }});
          </script>
        """, unsafe_allow_html=True)

# ----------------------------
# 4) Server-side PDF writer
# ----------------------------
def edit_pdf_with_elements(pdf_bytes: bytes, text_elements):
    """วาง text overlay ตาม page, x,y,font,size,color แล้ว merge ทับ PDF"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    width, height = A4

    elements_by_page = {}
    for el in text_elements or []:
        p = int(el.get('page', 1))
        elements_by_page.setdefault(p, []).append(el)

    for page_num, page in enumerate(reader.pages, start=1):
        if page_num in elements_by_page:
            buf = io.BytesIO()
            can = canvas.Canvas(buf, pagesize=A4)
            for el in elements_by_page[page_num]:
                text = str(el.get('text', ''))
                x = float(el.get('x', 50))
                y = float(el.get('y', 50))
                font = el.get('font', 'Helvetica')
                size = int(el.get('fontSize', 16))
                color = el.get('color', '#111111')
                try:
                    c = color.lstrip('#'); r,g,b = (int(c[i:i+2],16)/255 for i in (0,2,4))
                except Exception:
                    r=g=b=0
                can.setFillColorRGB(r,g,b)
                try:
                    if font in ["THSarabunPSK","THSarabunNew"] and FONTS_AVAILABLE:
                        fp = os.path.join("fonts", f"{font}.ttf")
                        if os.path.exists(fp):
                            pdfmetrics.registerFont(ttfonts.TTFont(font, fp))
                            can.setFont(font, size)
                        else:
                            can.setFont('Helvetica', size)
                    else:
                        can.setFont(font, size)
                except Exception:
                    can.setFont('Helvetica', size)
                y_pdf = height - y - size
                can.drawString(x, y_pdf, text)
            can.save(); buf.seek(0)
            overlay = PdfReader(buf)
            page.merge_page(overlay.pages[0])
        writer.add_page(page)
    out = io.BytesIO(); writer.write(out); out.seek(0)
    return out

# ----------------------------
# 5) Fullscreen interactive editor (pdf24-like)
# ----------------------------
def interactive_pdf_editor_fullscreen(pdf_bytes: bytes | None, total_pages:int):
    pdf_b64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

    # embed Thai fonts to browser (optional)
    custom_font_css = ""
    for fname in ["THSarabunPSK", "THSarabunNew"]:
        fp = os.path.join("fonts", f"{fname}.ttf")
        if os.path.exists(fp):
            try:
                with open(fp, "rb") as f: b64 = base64.b64encode(f.read()).decode()
                custom_font_css += """
                @font-face {{
                  font-family:'{fname}';
                  src:url(data:font/ttf;base64,{b64}) format('truetype');
                  font-weight:400; font-style:normal; font-display:swap;
                }}
                """.format(fname=fname, b64=b64)
            except Exception:
                pass

    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
      <style>
        %s
      </style>
    </head>
    <body>
      <div class="editor-shell">
        <!-- Left: Thumbnails -->
        <div class="panel">
          <div class="panel-header">หน้าเอกสาร</div>
          <div class="panel-body" id="thumbs"></div>
        </div>

        <!-- Center: Viewer -->
        <div class="panel viewer-wrap">
          <div class="toolbar" id="toolbar">
            <div class="group info-chip">
              <span id="pageInfo">Page 1 / %d</span>
            </div>
            <div class="group seg">
              <button id="prevBtn">◀</button>
              <button id="nextBtn">▶</button>
            </div>
            <div class="group seg" style="margin-left:8px">
              <button id="zoomOut">−</button>
              <button id="zoomReset">100%%</button>
              <button id="zoomIn">＋</button>
            </div>
            <div class="group" style="margin-left:auto">
              <button id="addText" class="btn">➕ เพิ่มข้อความ</button>
              <button id="clearPage" class="btn" title="ล้างข้อความหน้าปัจจุบัน">🗑️ ล้างหน้านี้</button>
            </div>
          </div>

          <div class="viewer" id="viewer">
            <div class="page-holder" id="pageHolder">
              <canvas id="pdfCanvas" class="pdf-canvas" width="595" height="842"></canvas>
              <div class="text-layer" id="textLayer"></div>
            </div>
          </div>
        </div>

        <!-- Right: Properties -->
        <div class="panel">
          <div class="panel-header">คุณสมบัติ</div>
          <div class="panel-body props-body">
            <label>ข้อความ</label>
            <textarea id="propText" rows="3" placeholder="เลือกกล่องข้อความเพื่อแก้ไข"></textarea>
            <div class="row">
              <div>
                <label>ฟอนต์</label>
                <select id="propFont">
                  <option value="Helvetica">Helvetica</option>
                  <option value="Times-Roman">Times New Roman</option>
                  <option value="Courier">Courier</option>
                  <option value="THSarabunPSK">TH Sarabun PSK</option>
                  <option value="THSarabunNew">TH Sarabun New</option>
                </select>
              </div>
              <div>
                <label>ขนาด</label>
                <input type="number" id="propSize" value="16" min="8" max="96"/>
              </div>
            </div>
            <div>
              <label>สี</label>
              <input type="color" id="propColor" value="#111111"/>
            </div>
            <div class="row">
              <div>
                <label>X</label>
                <input type="number" id="propX" value="50" min="0" max="595"/>
              </div>
              <div>
                <label>Y</label>
                <input type="number" id="propY" value="50" min="0" max="842"/>
              </div>
            </div>
            <div>
              <button id="deleteBox" class="btn" style="background:#fff0f0;border-color:#fecaca;color:#b91c1c">ลบกล่อง</button>
            </div>
            <hr/>
            <small style="color:#64748b">ปล่อยเมาส์เมื่อย้าย/ปรับขนาด ระบบจะส่งข้อมูลกลับไป Streamlit อัตโนมัติ</small>
          </div>
        </div>
      </div>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <script>
      // ---------- Helpers ----------
      const pdfDataB64 = '%s';
      function b642u8(b){const r=atob(b); const a=new Uint8Array(r.length); for(let i=0;i<r.length;i++) a[i]=r.charCodeAt(i); return a;}
      const CSS_FONT_MAP = {
        "Helvetica":"Helvetica, Arial, sans-serif",
        "Times-Roman":"'Times New Roman', Times, serif",
        "Courier":"'Courier New', Courier, monospace",
        "THSarabunPSK":"'THSarabunPSK','Sarabun','Noto Sans Thai',sans-serif",
        "THSarabunNew":"'THSarabunNew','Sarabun','Noto Sans Thai',sans-serif"
      };
      function cssFont(n){return CSS_FONT_MAP[n] || n;}

      // ---------- State ----------
      let pdfDoc=null; let currentPage=1; const totalPages=%d;
      let zoom=1.0; let baseW=595, baseH=842;
      let textElements=[]; let idCounter=0;
      let selectedId=null; let dragMode=null; // 'move' or 'resize'
      let startX=0, startY=0, startLeft=0, startTop=0, startSize=16;

      // ---------- DOM ----------
      const pdfCanvas = document.getElementById('pdfCanvas');
      const ctx = pdfCanvas.getContext('2d');
      const pageHolder = document.getElementById('pageHolder');
      const textLayer = document.getElementById('textLayer');
      const pageInfo = document.getElementById('pageInfo');
      const viewer = document.getElementById('viewer');
      const thumbs = document.getElementById('thumbs');

      const propText = document.getElementById('propText');
      const propFont = document.getElementById('propFont');
      const propSize = document.getElementById('propSize');
      const propColor= document.getElementById('propColor');
      const propX = document.getElementById('propX');
      const propY = document.getElementById('propY');
      const deleteBox = document.getElementById('deleteBox');

      // ---------- PDF load ----------
      pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
      if(pdfDataB64){
        pdfjsLib.getDocument({data:b642u8(pdfDataB64)}).promise.then(pdf=>{
          pdfDoc = pdf;
          buildThumbnails();
          renderPage(1);
        });
      }

      function buildThumbnails(){
        thumbs.innerHTML='';
        for(let i=1;i<=totalPages;i++){
          const wrap=document.createElement('div');
          wrap.className='thumb'; wrap.dataset.page=i;
          const c=document.createElement('canvas'); c.width=160; c.height=226;
          wrap.appendChild(c); thumbs.appendChild(wrap);
          pdfDoc.getPage(i).then(p=>{
            const vp=p.getViewport({scale:1});
            const s=Math.min(c.width/vp.width, c.height/vp.height);
            const v=p.getViewport({scale:s});
            c.width=v.width; c.height=v.height;
            p.render({canvasContext:c.getContext('2d'), viewport:v});
          });
          wrap.addEventListener('click',()=>{ renderPage(i); });
        }
      }

      // ---------- Render ----------
      function renderPage(n){
        currentPage = n;
        pageInfo.textContent = `Page ${n} / ${totalPages}`;
        [...thumbs.children].forEach(el=> el.classList.toggle('active', parseInt(el.dataset.page,10)===n));

        pdfDoc.getPage(n).then(p=>{
          const unscaled = p.getViewport({scale:1});
          const s = Math.min(baseW/unscaled.width, baseH/unscaled.height);
          const vp = p.getViewport({scale:s});
          pdfCanvas.width = vp.width; pdfCanvas.height = vp.height;
          pageHolder.style.width = vp.width+'px';
          pageHolder.style.height = vp.height+'px';
          return p.render({canvasContext:ctx, viewport:vp}).promise;
        }).then(()=>{
          redrawTextLayer();
        });
      }

      function redrawTextLayer(){
        textLayer.innerHTML='';
        textElements.filter(e=>e.page===currentPage).forEach(drawBox);
        applyZoom();
      }

      // ---------- Zoom ----------
      function applyZoom(){
        pageHolder.style.transform = `scale(${zoom})`;
      }
      document.getElementById('zoomIn').onclick = ()=>{ zoom=Math.min(2.4, zoom+0.1); applyZoom(); };
      document.getElementById('zoomOut').onclick= ()=>{ zoom=Math.max(0.5, zoom-0.1); applyZoom(); };
      document.getElementById('zoomReset').onclick=()=>{ zoom=1.0; applyZoom(); };

      // ---------- Navigation ----------
      document.getElementById('prevBtn').onclick=()=>{ if(currentPage>1) renderPage(currentPage-1); };
      document.getElementById('nextBtn').onclick=()=>{ if(currentPage<totalPages) renderPage(currentPage+1); };

      // ---------- Text boxes ----------
      document.getElementById('addText').onclick = ()=>{
        const el={ id: ++idCounter, page: currentPage, text:'Text',
          x: 50, y: 50, font:'Helvetica', fontSize:16, color:'#111111'
        };
        textElements.push(el); drawBox(el); select(el.id); postElements();
      };
      document.getElementById('clearPage').onclick = ()=>{
        if(!confirm('ล้างข้อความบนหน้านี้ทั้งหมด?')) return;
        textElements = textElements.filter(e=>e.page!==currentPage);
        redrawTextLayer(); postElements();
      };

      function drawBox(el){
        const d=document.createElement('div'); d.className='text-element'; d.id=`t-${el.id}`;
        d.style.left=el.x+'px'; d.style.top=el.y+'px';
        d.style.fontFamily=cssFont(el.font); d.style.fontSize=el.fontSize+'px'; d.style.color=el.color;
        d.textContent=el.text;

        const del=document.createElement('button'); del.className='delete-btn'; del.textContent='×';
        del.onclick=(e)=>{ e.stopPropagation(); removeBox(el.id); };
        const rh=document.createElement('div'); rh.className='resize-handle';

        d.appendChild(del); d.appendChild(rh); textLayer.appendChild(d);

        d.addEventListener('mousedown', (e)=>{
          if(e.target===rh){ dragMode='resize'; startY=e.clientY; startSize=el.fontSize; }
          else{ dragMode='move'; startX=e.clientX; startY=e.clientY; startLeft=el.x; startTop=el.y; }
          select(el.id);
        });

        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);

        function onMove(e){
          if(selectedId!==el.id) return;
          if(dragMode==='move'){
            const dx=(e.clientX-startX)/zoom, dy=(e.clientY-startY)/zoom;
            el.x=Math.max(0, Math.min(startLeft+dx, pdfCanvas.width-4));
            el.y=Math.max(0, Math.min(startTop+dy,  pdfCanvas.height-4));
            d.style.left=el.x+'px'; d.style.top=el.y+'px';
            syncProps(el);
          } else if(dragMode==='resize'){
            const dy=(e.clientY-startY)/zoom;
            el.fontSize=Math.max(8, Math.min(96, startSize+dy));
            d.style.fontSize=el.fontSize+'px'; syncProps(el);
          }
        }
        function onUp(){
          if(dragMode){ postElements(); }
          dragMode=null;
        }
      }

      function select(id){
        selectedId=id;
        [...document.querySelectorAll('.text-element')].forEach(n=>n.classList.remove('selected'));
        const d=document.getElementById(`t-${id}`); d?.classList.add('selected');
        const el = textElements.find(x=>x.id===id); if(el){ loadProps(el); }
      }
      function loadProps(el){
        propText.value=el.text; propFont.value=el.font; propSize.value=el.fontSize;
        propColor.value=el.color; propX.value=el.x; propY.value=el.y;
      }
      function syncProps(el){
        if(selectedId!==el.id) return;
        propX.value=Math.round(el.x); propY.value=Math.round(el.y);
        propSize.value=Math.round(el.fontSize);
      }
      function updateFromProps(){
        if(!selectedId) return;
        const el = textElements.find(x=>x.id===selectedId); if(!el) return;
        el.text=propText.value; el.font=propFont.value; el.fontSize=parseInt(propSize.value)||16; el.color=propColor.value;
        el.x=parseFloat(propX.value)||0; el.y=parseFloat(propY.value)||0;
        const d=document.getElementById(`t-${el.id}`);
        if(d){
          d.textContent=el.text;
          // re-append controls
          const del=document.createElement('button'); del.className='delete-btn'; del.textContent='×';
          del.onclick=(e)=>{ e.stopPropagation(); removeBox(el.id); };
          const rh=document.createElement('div'); rh.className='resize-handle';
          d.innerHTML=''; d.appendChild(del); d.appendChild(rh); d.append(el.text);
          d.style.left=el.x+'px'; d.style.top=el.y+'px';
          d.style.fontFamily=cssFont(el.font); d.style.fontSize=el.fontSize+'px'; d.style.color=el.color;
        }
        postElements();
      }
      propText.oninput=updateFromProps;
      propFont.onchange=updateFromProps;
      propSize.onchange=updateFromProps;
      propColor.onchange=updateFromProps;
      propX.onchange=updateFromProps;
      propY.onchange=updateFromProps;

      function removeBox(id){
        textElements = textElements.filter(x=>x.id!==id);
        const d=document.getElementById(`t-${id}`); d?.remove();
        selectedId=null; postElements();
      }
      deleteBox.onclick=()=>{ if(selectedId) removeBox(selectedId); };

      // ---------- Post to Streamlit ----------
      function postElements(){
        const msg = { isStreamlitMessage:true, type:"streamlit:setComponentValue", value: JSON.stringify(textElements) };
        window.parent.postMessage(msg, "*");
      }
      // init
      postElements();
      </script>
    </body>
    </html>
    """ % (custom_font_css, total_pages, pdf_b64, total_pages)

    return components.html(html, height=900, scrolling=False)

# ----------------------------
# 6) Pages
# ----------------------------
def render_editor_page():
    up = st.file_uploader("อัปโหลดไฟล์ PDF", type="pdf", key="edit_pdf")
    if up:
        pdf_bytes = up.getvalue()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total = len(reader.pages)

        st.markdown('<div class="header-card"><h1>Interactive PDF Editor (Fullscreen)</h1><p>ลาก/ย้าย/ปรับขนาดกล่องข้อความได้ทันที ระบบจะสร้างไฟล์ใหม่อัตโนมัติ</p></div>', unsafe_allow_html=True)

        elements_json = interactive_pdf_editor_fullscreen(pdf_bytes, total)

        # เก็บ elements ใน session และสร้างไฟล์ใหม่อัตโนมัติ
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
                out = edit_pdf_with_elements(pdf_bytes, elements)
                st.success("ไฟล์อัปเดตแล้ว (อัตโนมัติ)")
                st.download_button("📥 ดาวน์โหลด PDF ที่แก้ไขแล้ว", data=out, file_name="edited_"+up.name, mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"❌ สร้างไฟล์ไม่สำเร็จ: {e}")

        with col1:
            st.markdown("#### 🧾 รายการข้อความ")
            if elements:
                for i, el in enumerate(elements,1):
                    st.write(f"**{i}.** Page {el.get('page',1)} | `{str(el.get('text',''))[:60]}` | ฟอนต์:{el.get('font')} | ขนาด:{el.get('fontSize')} | pos:({el.get('x')},{el.get('y')})")
                with st.expander("ดู JSON"):
                    st.json(elements)
            else:
                st.info("ยังไม่มีข้อความ")

def render_merger_page():
    st.markdown('<div class="header-card"><h1>รวมไฟล์ PDF</h1><p>อัปโหลดหลายไฟล์เพื่อรวมเป็นไฟล์เดียว</p></div>', unsafe_allow_html=True)
    files = st.file_uploader("เลือกไฟล์ (หลายไฟล์)", type="pdf", accept_multiple_files=True, key="merge_files")
    if files and len(files)>1:
        if st.button("รวมไฟล์", use_container_width=True):
            merger = PdfMerger()
            for f in files:
                merger.append(io.BytesIO(f.getvalue()))
            out=io.BytesIO(); merger.write(out); merger.close(); out.seek(0)
            st.success("✅ รวมไฟล์สำเร็จ")
            st.download_button("📥 ดาวน์โหลด", data=out, file_name="merged.pdf", mime="application/pdf", use_container_width=True)

def render_settings_page():
    st.markdown('<div class="header-card"><h1>ตั้งค่า</h1><p>ปรับแต่งธีม/ข้อมูลเวอร์ชัน</p></div>', unsafe_allow_html=True)
    st.code("Version: 1.2.0 (Fullscreen UI + thumbnails + st.rerun fix)")

# ----------------------------
# 7) App shell
# ----------------------------
st.markdown('<div class="header-card"><h1>📄 PDF Manager Pro — Fullscreen Edition</h1><p>UI เต็มหน้าแบบ pdf24 • ซูม • เลือกหน้า • Thumbnail • กล่องข้อความซ้อน</p></div>', unsafe_allow_html=True)

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
<hr style="margin:20px 0; opacity:.2">
<div style='text-align:center; color:#64748b'>© 2025 PDF Manager Pro – Streamlit</div>
""", unsafe_allow_html=True)
