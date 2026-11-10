import {useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

type Trace = {id:string;route:string;category:string;stages:string[];latency_ms:number;input_tokens:number;output_tokens:number;token_source:string;failure:string|null};
type Reply = {message:string;resource:{id:string;title:string;action:string};trace:Trace};
type Metrics = {requests:number;cache_hits:number;model_routes:number;fallbacks:number;p95_ms:number;tokens:Record<string,{input:number;output:number}>};
const examples = ['Help me arrange an appointment.', 'I need help getting there.', 'Can someone explain payment options?', 'I am a caregiver and need someone to talk to.'];
function App(){
 const [scope]=useState(()=>crypto.randomUUID());
 const [message,setMessage]=useState(examples[1]);
 const [reply,setReply]=useState<Reply|null>(null);
 const [traces,setTraces]=useState<Trace[]>([]);
 const [metrics,setMetrics]=useState<Metrics|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 async function submit(event:React.FormEvent){
  event.preventDefault(); if(busy||!message.trim())return;
  setBusy(true);setError('');
  try{
   const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scope,message,synthetic:true})});
   if(!response.ok)throw new Error(`Request failed (${response.status}). Please try again.`);
   setReply(await response.json() as Reply);
   const [t,m]=await Promise.all([fetch(`/api/traces?scope=${scope}`),fetch(`/api/metrics?scope=${scope}`)]);
   if(!t.ok||!m.ok)throw new Error('The answer is available, but the monitoring view could not be refreshed.');
   setTraces(await t.json() as Trace[]);setMetrics(await m.json() as Metrics);
  }catch(e){setError(e instanceof Error?e.message:'Something went wrong.');}
  finally{setBusy(false);}
 }
 return <main>
  <header><span className="eyebrow">ENGINEERING WORK SAMPLE</span><h1>Care Navigation Console</h1><p>Find the next logistical step. See how the agent reached it.</p></header>
  <aside><strong>Synthetic demo only.</strong> Use fictional requests. Resources are invented. This is not a patient service or medical advice.</aside>
  <div className="layout"><section className="panel"><h2>Ask for support</h2><form onSubmit={submit}><label htmlFor="request">Fictional navigation request</label><textarea id="request" maxLength={600} value={message} onChange={e=>setMessage(e.target.value)}/><div className="examples">{examples.map(example=><button key={example} type="button" onClick={()=>setMessage(example)}>{example}</button>)}</div><button className="primary" disabled={busy||!message.trim()}>{busy?'Finding a next step…':'Find a next step'}</button></form><div role="alert">{error}</div><div aria-live="polite">{reply&&<article className="result"><span className="badge">{reply.trace.category}</span><h3>{reply.resource.title}</h3><p>{reply.message}</p><small>{reply.trace.route} · {reply.trace.latency_ms.toFixed(1)} ms · {reply.resource.id}</small></article>}</div></section>
  <section className="panel"><h2>Session performance</h2><p>Send the same request twice to observe a cache hit. Refreshing starts a new scope.</p><div className="stats"><div><b>{metrics?.requests??0}</b><span>Requests</span></div><div><b>{metrics?.cache_hits??0}</b><span>Cache hits</span></div><div><b>{metrics?.p95_ms.toFixed(1)??'0'}</b><span>p95 · ms</span></div><div><b>{metrics?.fallbacks??0}</b><span>Fallbacks</span></div></div><h3>Token accounting</h3><p className="muted">Fixture estimates and provider-reported usage are kept separate. Cache hits do not add model tokens. Failed calls may be billable and are not included in this estimate.</p>{metrics&&Object.entries(metrics.tokens).map(([source,tokens])=><p key={source}><code>{source}</code>: {tokens.input} input / {tokens.output} output</p>)}</section></div>
  <section className="panel"><h2>Execution traces</h2><p>Bounded in-memory traces omit request text. This demo has no authentication.</p><div className="table-wrap"><table><thead><tr><th>Route</th><th>Action</th><th>Latency</th><th>Stages</th><th>Status</th></tr></thead><tbody>{traces.map(trace=><tr key={trace.id}><td>{trace.route}</td><td>{trace.category}</td><td>{trace.latency_ms.toFixed(1)} ms</td><td>{trace.stages.join(' → ')}</td><td>{trace.failure??'OK'}</td></tr>)}</tbody></table>{traces.length===0&&<p className="empty">Run a fictional request to inspect its path.</p>}</div></section>
 </main>;
}
createRoot(document.getElementById('root')!).render(<App/>);
