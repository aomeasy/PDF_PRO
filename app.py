def interactive_pdf_editor_fullscreen(pdf_bytes: bytes | None, total_pages:int):
    import base64, os
    pdf_b64 = base64.b64encode(pdf_bytes).decode() if pdf_bytes else ""

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
        /* เพิ่มเติมสำหรับการมองเห็นที่ชัดขึ้น */
        .toast{position:fixed; left:50%%; top:18px; transform:translateX(-50%%);
               background:#111827; color:#fff; padding:8px 12px; border-radius:10px;
               box-shadow:0 8px 24px rgba(0,0,0,.15); font-size:.9rem; z-index:9999; opacity:0; transition:opacity .2s;}
        .toast.show{opacity:1;}
        .text-element.added-hl{ box-shadow:0 0 0 3px rgba(59,130,246,.35) inset; background:rgba(59,130,246,.08); }
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
            <div class="group info-chip"><span id="pageInfo">Page 1 / %d</span></div>
            <div class="group seg">
              <button id="prevBtn">◀</button>
              <button id="nextBtn">▶</button>
            </div>
            <div class="group seg" style="margin-left:8px">
              <button id="zoomOut">−</button>
              <button id="zoomReset">100%%</button>
              <button id="zoomIn">＋</button>
              <button id="zoomFit" title="Fit to width">Fit</button>
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
              <div><label>X</label><input type="number" id="propX" value="50" min="0" max="595"/></div>
              <div><label>Y</label><input type="number" id="propY" value="50" min="0" max="842"/></div>
            </div>
            <div><button id="deleteBox" class="btn" style="background:#fff0f0;border-color:#fecaca;color:#b91c1c">ลบกล่อง</button></div>
            <hr/><small style="color:#64748b">ปล่อยเมาส์เมื่อย้าย/ปรับขนาด ระบบจะส่งข้อมูลกลับไป Streamlit อัตโนมัติ</small>
          </div>
        </div>
      </div>

      <div id="toast" class="toast">เพิ่มข้อความแล้ว</div>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <script>
      // ===== Helpers =====
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
      function showToast(msg){ const t=document.getElementById('toast'); t.textContent=msg||t.textContent; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),1200); }

      // ===== State =====
      let pdfDoc=null; let currentPage=1; const totalPages=%d;
      let zoom=1.0; let baseW=595, baseH=842;
      let textElements=[]; let idCounter=0;
      let selectedId=null; let dragMode=null;
      let startX=0, startY=0, startLeft=0, startTop=0, startSize=16;

      // ===== DOM =====
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

      // ===== PDF load =====
      pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
      if(pdfDataB64){
        pdfjsLib.getDocument({data:b642u8(pdfDataB64)}).promise.then(pdf=>{
          pdfDoc = pdf;
          buildThumbnails();
          renderPage(1, true); // true = doFit
        });
      }

      function buildThumbnails(){
        thumbs.innerHTML='';
        for(let i=1;i<=totalPages;i++){
          const wrap=document.createElement('div'); wrap.className='thumb'; wrap.dataset.page=i;
          const c=document.createElement('canvas'); c.width=160; c.height=226;
          wrap.appendChild(c); thumbs.appendChild(wrap);
          pdfDoc.getPage(i).then(p=>{
            const vp=p.getViewport({scale:1});
            const s=Math.min(c.width/vp.width, c.height/vp.height);
            const v=p.getViewport({scale:s});
            c.width=v.width; c.height=v.height;
            p.render({canvasContext:c.getContext('2d'), viewport:v});
          });
          wrap.addEventListener('click',()=>{ renderPage(i, true); });
        }
      }

      // ===== Render =====
      function renderPage(n, doFit=false){
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
          if(doFit) fitToWidth();
        });
      }

      function redrawTextLayer(){
        textLayer.innerHTML='';
        textElements.filter(e=>e.page===currentPage).forEach(drawBox);
        applyZoom();
      }

      // ===== Zoom & Fit =====
      function applyZoom(){ pageHolder.style.transform = `scale(${zoom})`; }
      function fitToWidth(){
        const vw = viewer.clientWidth || viewer.getBoundingClientRect().width;
        const canvasW = pdfCanvas.width;
        if(canvasW>0){
          const pad = 48; // margin
          zoom = Math.max(0.5, Math.min(2.4, (vw - pad)/canvasW));
          applyZoom();
        }
      }
      window.addEventListener('resize', ()=>fitToWidth());

      document.getElementById('zoomIn').onclick = ()=>{ zoom=Math.min(2.4, zoom+0.1); applyZoom(); };
      document.getElementById('zoomOut').onclick= ()=>{ zoom=Math.max(0.5, zoom-0.1); applyZoom(); };
      document.getElementById('zoomReset').onclick=()=>{ zoom=1.0; applyZoom(); };
      document.getElementById('zoomFit').onclick = ()=> fitToWidth();

      // ===== Navigation =====
      document.getElementById('prevBtn').onclick=()=>{ if(currentPage>1) renderPage(currentPage-1, true); };
      document.getElementById('nextBtn').onclick=()=>{ if(currentPage<totalPages) renderPage(currentPage+1, true); };

      // ===== Text boxes =====
      document.getElementById('addText').onclick = ()=>{
        const el={ id: ++idCounter, page: currentPage, text:'ข้อความใหม่',
          x: 80, y: 80, font:'Helvetica', fontSize:20, color:'#111111'
        };
        textElements.push(el);
        const node = drawBox(el);
        // Auto-select + highlight + scroll to center + focus prop
        select(el.id);
        node.classList.add('added-hl'); setTimeout(()=>node.classList.remove('added-hl'), 900);
        // scroll ให้กล่องอยู่กลาง viewport
        const rect = node.getBoundingClientRect();
        viewer.scrollBy({ left: rect.left - viewer.clientWidth/2 + rect.width/2, top: rect.top - viewer.clientHeight/2 + rect.height/2, behavior:'smooth' });
        propText.focus();
        showToast('เพิ่มข้อความแล้ว');
        postElements();
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
        d.append(document.createTextNode(el.text));

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
        function onUp(){ if(dragMode){ postElements(); } dragMode=null; }
        return d;
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
          // rebuild children to preserve controls
          d.innerHTML='';
          d.append(document.createTextNode(el.text));
          const del=document.createElement('button'); del.className='delete-btn'; del.textContent='×';
          del.onclick=(e)=>{ e.stopPropagation(); removeBox(el.id); };
          const rh=document.createElement('div'); rh.className='resize-handle';
          d.appendChild(del); d.appendChild(rh);
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
        if(selectedId===id) selectedId=null;
        postElements();
      }
      deleteBox.onclick=()=>{ if(selectedId) removeBox(selectedId); };

      // ===== Post to Streamlit =====
      function postElements(){
        const msg = { isStreamlitMessage:true, type:"streamlit:setComponentValue", value: JSON.stringify(textElements) };
        window.parent.postMessage(msg, "*");
      }
      </script>
    </body>
    </html>
    """ % (custom_font_css, total_pages, pdf_b64, total_pages)

    return components.html(html, height=900, scrolling=False)
