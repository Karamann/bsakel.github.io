const $=id=>document.getElementById(id);
const pairing=$("token"),status=$("status");
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
    else if(data.status==="ready")status.textContent="Ready on your Garmin. Tap GPS/START to refresh.";
    else status.textContent=data.status||"Connected";
  }catch(err){status.textContent=err.message;}
}
async function send(path,body){
  status.textContent="Sending…";
  try{
    await api(path,"POST",body);
    await refresh();
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