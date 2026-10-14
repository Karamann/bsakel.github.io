const $=id=>document.getElementById(id);
const pairing=$("token"),status=$("status");
let historySignature="";
pairing.value=localStorage.getItem("garminToken")||"";
function getToken(){
  const t=pairing.value.trim();
  if(!t)throw new Error("Enter your pairing token first.");
  localStorage.setItem("garminToken",t);
  return t;
}
async function api(path,method="GET",body){
  const token=getToken();
  const response=await fetch(path,{
    method,cache:"no-store",
    headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json"},
    body:body===undefined?undefined:JSON.stringify(body)
  });
  const json=await response.json();
  if(!response.ok)throw new Error(json.detail||("Request failed ("+response.status+")"));
  return json;
}
async function refresh(){
  try{
    const data=await api("/api/latest");
    $("answer").textContent=data.status==="thinking"?"Thinking…":data.answer||"No message yet.";
    if(data.status==="thinking")status.textContent="Generating...";
    else if(data.status==="ready")status.textContent="Ready on Garmin. Tap GPS/START to refresh.";
    else status.textContent=data.status||"Connected";
    $("sectionCount").textContent=data.sections?("Section "+data.section+" of "+data.sections+" on watch"):"No selected answer";
  }catch(err){status.textContent=err.message;}
}
async function send(path,body){
  status.textContent="Sending…";
  try{
    await api(path,"POST",body);
    await refresh();
    await loadHistory();
    return true;
  }catch(err){
    status.textContent=err.message;
    return false;
  }
}
$("sendClipboard").onclick=async ()=>{
  try{
    if(!navigator.clipboard||!navigator.clipboard.readText)throw new Error("Clipboard permission unavailable");
    const text=(await navigator.clipboard.readText()).trim();
    if(!text){status.textContent="Clipboard is empty. Copy a ChatGPT answer first.";return;}
    await send("/api/relay",{text});
  }catch(err){
    status.textContent="iPhone blocked direct clipboard access. Expand 'Paste manually' below, paste the copied answer, and tap Send pasted answer.";
    $("copied").focus();
  }
};
$("sendPasted").onclick=async ()=>{
  const text=$("copied").value.trim();
  if(!text){status.textContent="Paste the ChatGPT answer first.";return;}
  if(await send("/api/relay",{text}))$("copied").value="";
};
$("send").onclick=()=>{
  const question=$("question").value.trim();
  if(!question){status.textContent="Enter a question first.";return;}
  send("/api/prompt",{question});
};
$("demo").onclick=()=>send("/api/demo");
$("refresh").onclick=refresh;
pairing.onchange=()=>localStorage.setItem("garminToken",pairing.value.trim());
setInterval(()=>{if(pairing.value.trim())refresh();},7000);
if(pairing.value)refresh();
async function loadHistory(){
  try{
    const response=await api("/api/history");
    const rows=response.messages||[];
    const signature=rows.map(m=>m.id+":"+m.status).join(",");
    if(signature===historySignature)return;
    historySignature=signature;
    const dropdown=$("history");
    const selected=dropdown.value;
    dropdown.replaceChildren();
    for(const item of rows){
      const option=document.createElement("option");
      option.value=String(item.id);
      const short=(item.preview||item.question||"").replace(/\s+/g," ").slice(0,70);
      option.textContent="#"+item.id+" · "+(short||item.status);
      dropdown.appendChild(option);
    }
    if(!rows.length){
      const option=document.createElement("option");
      option.value="";
      option.textContent="No saved messages";
      dropdown.appendChild(option);
    }else if(rows.some(m=>String(m.id)===selected)){
      dropdown.value=selected;
    }
  }catch(err){/* Watch may still be accessible if history request fails */ }
}
async function storageStatus(){
  try{
    const response=await fetch("/health",{cache:"no-store"});
    const data=await response.json();
    $("persistenceWarning").textContent=data.persistent?
      "Persistent storage connected. Reopening the watch reloads the saved answer.":
      "Temporary server storage: the watch reloads after closing, but a server restart may erase history. Connect DATABASE_URL for durable retention.";
  }catch(err){
    $("persistenceWarning").textContent="Unable to verify whether saved answers are persistent.";
  }
}
$("showHistory").onclick=async ()=>{
  const id=Number($("history").value);
  if(!id)return;
  if(await send("/api/select",{id})){
    status.textContent="Saved answer selected. Your Garmin will retrieve it automatically.";
  }
};
$("previousSection").onclick=()=>send("/api/section",{delta:-1});
$("nextSection").onclick=()=>send("/api/section",{delta:1});
setInterval(()=>{if(pairing.value.trim())loadHistory();},15000);
setInterval(storageStatus,60000);
storageStatus();
if(pairing.value.trim())loadHistory();
