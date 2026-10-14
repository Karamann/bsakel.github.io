const $=id=>document.getElementById(id);const token=$("token"),status=$("status");
token.value=localStorage.getItem("garminToken")||"";
function key(){let t=token.value.trim();if(!t)throw Error("Enter pairing token");localStorage.setItem("garminToken",t);return t;}
async function api(path,method="GET",body){
 const r=await fetch(path,{method,headers:{"Authorization":"Bearer "+key(),"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined,cache:"no-store"});
 const d=await r.json();if(!r.ok)throw Error(d.detail||"Request failed");return d;
}
async function refresh(){try{
 const d=await api("/api/latest");
 $("answer").textContent=d.status==="thinking"?"Thinking...":d.answer||"No message yet";
 status.textContent=d.status==="ready"?"Ready to read on watch":d.status;
}catch(e){status.textContent=e.message;}}
async function send(path,body){try{await api(path,"POST",body);await refresh();}catch(e){status.textContent=e.message;}}
$("send").onclick=()=>send("/api/prompt",{question:$("question").value.trim()});
$("demo").onclick=()=>send("/api/demo");
$("refresh").onclick=refresh;
setInterval(()=>{if(token.value.trim())refresh();},7000);
if(token.value)refresh();