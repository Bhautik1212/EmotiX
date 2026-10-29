/* EmotiX API bridge. The original UI remains intact; this layer adds account and server persistence. */
(() => {
  const API = '/api';
  const $ = (s, r=document) => r.querySelector(s);
  let token = localStorage.getItem('emotix_token') || '';
  let user = null;
  let pendingChat = [];
  const headers = () => ({'Content-Type':'application/json', ...(token ? {Authorization:`Bearer ${token}`} : {})});
  async function request(path, opts={}) {
    const res = await fetch(API+path, {...opts, headers:{...headers(), ...(opts.headers||{})}});
    let data={}; try { data=await res.json(); } catch {}
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    return data;
  }
  function notice(msg) {
    let n=$('#apiNotice'); if(!n){n=document.createElement('div');n.id='apiNotice';n.className='toast';n.style.zIndex='999';document.body.append(n)}
    n.textContent=msg; n.hidden=false; clearTimeout(notice.timer); notice.timer=setTimeout(()=>n.hidden=true,3600);
  }
  function setAuth() {
    const el=$('#emotixAuthState'); if(!el)return;
    el.innerHTML = user ? `Signed in as <b>${escapeHtml(user.name||user.email)}</b> <button class="btn sm" id="emotixHistory">History</button> <button class="btn sm ghost" id="emotixLogout">Sign out</button>` : `<span class="mute">Not signed in</span> <button class="btn sm primary" id="emotixAuthOpen">Sign in / Create account</button>`;
    $('#emotixAuthOpen')?.addEventListener('click',openAuth);
    $('#emotixLogout')?.addEventListener('click',()=>{token='';user=null;localStorage.removeItem('emotix_token');setAuth();notice('Signed out.');});
    $('#emotixHistory')?.addEventListener('click',showHistory);
  }
  function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function setupUI(){
    const nav=$('.nav .links'); if(nav&&!$('#emotixAuthState')){const box=document.createElement('div');box.id='emotixAuthState';nav.append(box);}
    if(!$('#emotixAuthModal')){
      const modal=document.createElement('div');modal.id='emotixAuthModal';modal.hidden=true;modal.style.cssText='position:fixed;inset:0;z-index:1000;background:#030814dd;display:grid;place-items:center;padding:20px';
      modal.innerHTML=`<div class="card" style="width:min(460px,100%);box-shadow:0 20px 90px #000"><div class="row" style="justify-content:space-between"><h2 id="authTitle">Sign in to EmotiX</h2><button class="btn sm" id="authClose">Close</button></div><p class="mute" style="margin:12px 0 18px">Your saved assessments are private to your account. Use a unique password.</p><form id="authForm" class="form"><div class="fld" id="authNameWrap" hidden><label for="authName">Name</label><input class="in" id="authName" maxlength="120" autocomplete="name"></div><div class="fld"><label for="authEmail">Email</label><input class="in" id="authEmail" type="email" required autocomplete="email"></div><div class="fld"><label for="authPassword">Password</label><input class="in" id="authPassword" type="password" required minlength="10" maxlength="128" autocomplete="current-password"><small class="mute">At least 10 characters.</small></div><p id="authError" class="status err" hidden></p><button class="btn primary" id="authSubmit" type="submit">Sign in</button></form><button class="go" id="authToggle" style="margin-top:14px">Need an account? Create one</button></div>`;
      document.body.append(modal);
      $('#authClose').onclick=()=>modal.hidden=true;
      $('#authToggle').onclick=()=>{const create=$('#authNameWrap').hidden;$('#authNameWrap').hidden=!create;$('#authTitle').textContent=create?'Create EmotiX account':'Sign in to EmotiX';$('#authSubmit').textContent=create?'Create account':'Sign in';$('#authToggle').textContent=create?'Already have an account? Sign in':'Need an account? Create one';$('#authPassword').setAttribute('autocomplete',create?'new-password':'current-password');$('#authError').hidden=true;};
      $('#authForm').onsubmit=async e=>{e.preventDefault();const create=!$('#authNameWrap').hidden;const err=$('#authError');err.hidden=true;$('#authSubmit').disabled=true;try{const payload={email:$('#authEmail').value.trim(),password:$('#authPassword').value};if(create)payload.name=$('#authName').value.trim();const data=await request(create?'/auth/register':'/auth/login',{method:'POST',body:JSON.stringify(payload)});token=data.access_token;user=data.user;localStorage.setItem('emotix_token',token);modal.hidden=true;setAuth();notice(create?'Account created. You are signed in.':'Signed in successfully.');await syncPending();}catch(ex){err.textContent=ex.message;err.hidden=false;}finally{$('#authSubmit').disabled=false;}};
    }
    if(!$('#emotixHistoryPanel')){const p=document.createElement('div');p.id='emotixHistoryPanel';p.hidden=true;p.style.cssText='position:fixed;inset:0;z-index:1001;background:#030814dd;overflow:auto;padding:24px';p.innerHTML=`<div class="wrap card" style="margin:40px auto;max-width:900px"><div class="row" style="justify-content:space-between"><h2>Your saved history</h2><button class="btn" id="historyClose">Close</button></div><p class="mute" style="margin:10px 0 20px">Saved to the local EmotiX database. Scores are experimental, not diagnoses.</p><div id="historyRows">Loading…</div><div class="row" style="margin-top:18px"><button class="btn primary" id="historyPdf">Download PDF report</button><button class="btn danger" id="historyDelete">Delete my saved assessments</button></div></div>`;document.body.append(p);$('#historyClose').onclick=()=>p.hidden=true;$('#historyPdf').onclick=async()=>{try{const r=await fetch(API+'/report.pdf',{headers:headers()});if(!r.ok)throw new Error('Could not create report');const b=await r.blob(),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='EmotiX-report.pdf';a.click();URL.revokeObjectURL(a.href);}catch(e){notice(e.message)}};$('#historyDelete').onclick=async()=>{if(!confirm('Delete all saved assessments for this account?'))return;try{await request('/assessments',{method:'DELETE'});await showHistory();notice('Saved assessments deleted.');}catch(e){notice(e.message)}};}
    const banner=document.createElement('div');banner.className='wrap';banner.style.cssText='font-size:11px;color:#8fa1bf;padding:8px 0 0';banner.innerHTML='LOCAL PROTOTYPE · Assessment scores are experimental, not clinically validated. Webcam/voice emotion labels may be heuristic or model-dependent.';const first=$('#view-home .hero');if(first&&!$('#prototypeBanner')){banner.id='prototypeBanner';first.before(banner)}
    setAuth();
  }
  function openAuth(){ $('#emotixAuthModal').hidden=false; }
  async function showHistory(){const panel=$('#emotixHistoryPanel');panel.hidden=false;const root=$('#historyRows');root.textContent='Loading…';try{const rows=await request('/assessments');if(!rows.length){root.innerHTML='<p class="hist-empty">No saved assessments yet. Sign in and complete the behaviour assessment to start your history.</p>';return;}root.innerHTML=`<div class="scroll-x"><table class="t"><thead><tr><th>Date</th><th>Module</th><th>Score</th><th>Risk band</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${escapeHtml(new Date(r.created_at).toLocaleString())}</td><td>${escapeHtml(r.module)}</td><td>${Number(r.score).toFixed(1)}/10</td><td>${escapeHtml(r.risk_level)}</td></tr>`).join('')}</tbody></table></div>`;}catch(e){root.innerHTML=`<p class="status err">${escapeHtml(e.message)}</p>`;}}
  async function saveAssessment(module,score,payload){if(!user){pendingChat=[];notice('Sign in to save assessments and history. Your current browser assessment still works.');return;}try{await request('/assessments',{method:'POST',body:JSON.stringify({module,score,payload})});notice('Assessment saved to your account.');}catch(e){notice(e.message)}}
  async function syncPending(){if(!user)return;if(pendingChat.length){const batch=pendingChat.map(message=>({message}));pendingChat=[];try{await request('/chat/history',{method:'POST',body:JSON.stringify({messages:batch})});}catch{}}}
  async function init(){
    setupUI();
    try{if(token){user=await request('/auth/me');setAuth();}}catch{token='';user=null;localStorage.removeItem('emotix_token');setAuth();}
    try{const h=await request('/health',{headers:{}});document.documentElement.dataset.apiStatus=h.status;}catch{notice('API not reachable. Start the server using run_windows.bat.');}
    const bform=$('#bForm');if(bform)bform.addEventListener('submit',()=>{setTimeout(async()=>{const payload={name:$('#b-name').value,age:+$('#b-age').value,sleep:+$('#b-sleep').value,sleep_quality:+$('#b-sq').value,stress:+$('#b-stress').value,activity:+$('#b-act').value,steps:+$('#b-steps').value,heart_rate:+$('#b-hr').value,systolic:+$('#b-sys').value,diastolic:+$('#b-dia').value,height:+$('#b-height').value,weight:+$('#b-weight').value};const bmi=payload.weight/Math.pow((payload.height||172)/100,2);const risks={stress:payload.stress,sleepH:payload.sleep>=7&&payload.sleep<=9?1:payload.sleep<7?1+(7-payload.sleep)*2.25:1+(payload.sleep-9)*3,sleepQ:10-payload.sleep_quality,act:10-payload.activity,steps:payload.steps>=8000?1:1+(8000-payload.steps)/8000*9,bp:(payload.systolic>=160||payload.diastolic>=100)?9.5:(payload.systolic>=140||payload.diastolic>=90)?7.5:(payload.systolic>=130||payload.diastolic>=85)?5.5:(payload.systolic>=120||payload.diastolic>=80)?3:1,hr:payload.heart_rate>100?7:payload.heart_rate>85?4:payload.heart_rate>=60?1:payload.heart_rate>=50?2:5,bmi:bmi>=30?7:bmi>=25?4:bmi>=18.5?1:5};const rough=Math.max(0,Math.min(10,.28*risks.stress+.14*risks.sleepH+.14*risks.sleepQ+.10*risks.act+.10*risks.steps+.10*risks.bp+.07*risks.hr+.07*risks.bmi));const item={module:'behaviour',score:+rough.toFixed(2),payload};if(user)await saveAssessment(item.module,item.score,item.payload);else notice('Sign in before running an assessment to save it to your account. The browser assessment still works.');},0);},true);
    const cf=$('#cForm');if(cf)cf.addEventListener('submit',()=>{const input=$('#cIn');const message=input?.value?.trim();if(!message)return;if(user){request('/chat/history',{method:'POST',body:JSON.stringify({messages:[{message}]})}).catch(()=>{});}else{pendingChat.push(message); /* in memory only until sign-in */ }},true);
    const done=$('#chatDone');if(done)done.addEventListener('click',()=>{pendingChat=[];},true);
    document.addEventListener('click',e=>{const b=e.target.closest('[data-go="dashboard"]');if(!b)return;setTimeout(()=>{const scoreText=$('#dash-root')?.innerText||'';const m=scoreText.match(/([0-9]+(?:\.[0-9]+)?)\s*\/\s*10/);if(m){const item={module:'fused',score:Math.min(10,+m[1]),payload:{source:'existing browser fusion dashboard',prototype:true}};if(user)saveAssessment(item.module,item.score,item.payload);else notice('Sign in before saving a fused result to your account.');}},350);},true);
  }
  document.addEventListener('DOMContentLoaded',init);
})();
