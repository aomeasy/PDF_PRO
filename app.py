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
# Fonts for ReportLab (server-side PDF generation)
# ------------------------------------------------------------
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
    FONTS_AVAILABLE = True
except ImportError:
    FONTS_AVAILABLE = False

# ------------------------------------------------------------
# Page config + modern neutral UI
# ------------------------------------------------------------
st.set_page_config(page_title="PDF Manager Pro - Interactive", page_icon="📄", layout="wide")

st.markdown("""
<style>
:root{
  --bg:#f6f7fb; --card:#ffffff; --border:#e5e7eb;
  --text:#0f172a; --muted:#64748b;
  --primary:#111827; /* near-black */
  --accent:#2563eb;  /* blue-600 */
  --success:#10b981; /* emerald-500 */
  --danger:#ef4444;  /* red-500 */
}
html, body { background: var(--bg); }
.block-container { padding-top: 14px; }

/* Header */
.header-card{
  background: var(--card); color: var(--text);
  border: 1px solid var(--border);
  border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 8px 24px rgba(0,0,0,.06);
}
.header-card h1{ margin:0; font-size:1.35rem; font-weight:800; letter-spacing:.2px; }
.header-card p{ margin:6px 0 0; color:var(--muted); }

/* Action bar (sticky) */
.sticky-actions{ position: sticky; top: 0; z-index: 50; padding-top: 10px; }
.action-bar{
  background: var(--card); border:1px solid var(--border);
  border-radius: 12px; padding: 10px 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,.05);
  display:flex; align-items:center; justify-content:space-between; gap:10px;
  color:var(--muted);
}

/* Buttons */
.btn{ border:none; border-radius:10px; font-weight:700; cursor:pointer; padding:10px 14px; }
.btn-primary{ background: var(--primary); color:#fff; }
.btn-accent{ background: var(--accent); color:#fff; }
.btn-success{ background: var(--success); color:#fff; }
.btn-ghost{ background:#f3f4f6; color:var(--text); }
.btn:disabled{ opacity:.55; cursor:not-allowed; }

/* Cards */
.card{
  background:var(--card); border:1px solid var(--border);
  border-radius:16px; padding:16px;
  box-shadow:0 8px 24px rgba(0,0,0,.05);
}
.section-title{ font-weight:800; color:var(--text); margin-bottom:8px; }

/* Editor canvas */
.canvas-wrap{ padding:18px; }
.viewport{
  margin:0 auto; border:1px solid var(--border); border-radius:12px;
  background:#fff; box-shadow:0 8px 24px rgba(0,0,0,.05);
  overflow:auto;
}
#page{
  width:595px; height:842px; position:relative; transform-origin: top left;
}
#pdfCanvas{ position:absolute; top:0; left:0; width:595px; height:842px; pointer-events:none; }
.text-element{
  position:absolute; cursor:move; padding:4px 6px;
  border:2px dashed transparent; user-select:none; white-space:pre-wrap; z-index:10;
}
.text-element:hover{ border-color: var(--accent); background: rgba(37,99,235,.08); }
.text-element.selected{ border-color: var(--accent); background: rgba(37,99,235,.12); }
.delete-btn{
  position:absolute; top:-12px; right:-12px; width:24px; height:24px;
  background: var(--danger); color:#fff; border:none; border-radius:50%; cursor:pointer; display:none;
}
.text-element:hover .delete-btn{ display:block; }
.resize-handle{
  position:absolute; bottom:-5px; right:-5px; width:12px; height:12px;
  background: var(--accent); border-radius:50%; cursor:nwse-resize; display:none;
}
.text-element:hover .resize-handle{ display:block; }

/* Inputs on toolbar inside component */
.toolbar{
  display:grid; grid-template-columns: 1fr 150px 120px 120px 1fr;
  gap:10px; align-items:center; margin-bottom:10px;
}
.toolbar textarea, .toolbar select, .toolbar input[type="number"], .toolbar input[type="color"]{
  border:1px solid var(--border); border-radius:10px; padding:10px; font-size:14px; background:#fff;
}
.toolbar textarea{ grid-column: 1 / 6; min-height:60px; resize:vertical; }
.zoom-controls{ display:flex; gap:8px; align-items:center; justify-content:flex-end; }
.zoom-btn{ border:1px solid var(--border); background:#fff; border-radius:8px; padding:8px 10px; cursor:pointer; }
.zoom-value{ color:var(--muted); min-width:56px; text-align:center; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# PDF writer (server-side) – logic เดิม
# ------------------------------------------------------------
def edit_pdf_with_elements(pdf_bytes: bytes, text_elements):
    """สร้าง PDF ใหม่โดยเพิ่ม text overlay (base coordinate: A4 portrait ~ 595x842 px)"""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    width, height = A4

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

# ------------------------------------------------------------
# Interactive editor component
# - ส่ง elements กลับทุกครั้งที่ "mouse up" หรือมีการแก้ไข -> Streamlit จะสร้าง PDF ให้เอง
# - มี Zoom 50–200% (default 125%)
# ------------------------------------------------------------
def interactive_pdf_editor(pdf_bytes: bytes | None = None):
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
          view.style.width  = (BASE_W * currentZoom + 150) + 'px';   // give some space
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
          del.onclick = (e)=>{{ e.stopPropagation(); deleteText(el.id); }};
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
          textElements.forEach(x=>{{ const d=document.getElementById('text-'+x.id); if(d) d.remove(); }});
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
          const msg = {{ isStreamlitMessage: true, type: "streamlit:setComponentValue", value: payload }};
          window.parent.postMessage(msg, "*");
        }

        // initialize with empty
        postElements();
      </script>
    </body>
    </html>
    """
    return components.html(html, height=900, scrolling=True)

# ------------------------------------------------------------
# App shell
# ------------------------------------------------------------
st.markdown('<div class="header-card"><h1>📄 PDF Manager Pro — Interactive Edition</h1><p>ลาก-วางข้อความบนเอกสาร • Zoom ได้ • สร้างไฟล์ PDF อัตโนมัติ</p></div>', unsafe_allow_html=True)

feature = st.sidebar.radio("ฟังก์ชัน", ["✏️ แก้ไข PDF (Interactive)", "🔗 รวมไฟล์ PDF"])

# ------------------------------------------------------------
# Interactive editor flow (auto-generate PDF)
# ------------------------------------------------------------
if feature == "✏️ แก้ไข PDF (Interactive)":
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

# ------------------------------------------------------------
# Merge PDFs (เดิม)
# ------------------------------------------------------------
elif feature == "🔗 รวมไฟล์ PDF":
    st.markdown('<div class="card"><div class="section-title">🔗 รวมหลายไฟล์ PDF</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader("อัปโหลดไฟล์ PDF (หลายไฟล์)", type="pdf", accept_multiple_files=True, key="merge_files")
    if uploaded_files and len(uploaded_files) > 1:
        st.info(f"เลือก {len(uploaded_files)} ไฟล์")
        if st.button("รวมไฟล์", type="primary"):
            with st.spinner("กำลังรวมไฟล์..."):
                merger = PdfMerger()
                for pdf in uploaded_files:
                    merger.append(io.BytesIO(pdf.getvalue()))
                output = io.BytesIO()
                merger.write(output)
                merger.close()
                output.seek(0)
                st.success("✅ รวมไฟล์สำเร็จ!")
                st.download_button("📥 ดาวน์โหลดไฟล์ที่รวมแล้ว", data=output, file_name="merged.pdf", mime="application/pdf")
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.markdown("""
<hr style="margin:28px 0; opacity:.2">
<div style='text-align:center; color:#64748b'>
  © 2025 PDF Manager Pro – สร้างด้วย Streamlit
</div>
""", unsafe_allow_html=True)
