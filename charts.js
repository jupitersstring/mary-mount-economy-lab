/* All rights reserved. Written permission required. See LICENSE. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ECONOMY_CHARTS=api;})(typeof window==='object'?window:this,function(){
'use strict';
const finite=Number.isFinite;
const number=(v,n=2)=>!finite(v)?'Unavailable':new Intl.NumberFormat('en-GB',{maximumFractionDigits:n,minimumFractionDigits:0}).format(Math.abs(v)<.5*10**(-n)?0:v);
const signed=v=>(v>0?'+':'')+number(v);
function divide(value,denominator){return finite(value)&&finite(denominator)&&denominator>0?value/denominator:null;}
function points(rows,getter,perCapita){return rows.map(r=>{const value=getter(r);return [r.t,perCapita?divide(value,r.labour):finite(value)?value:null];});}
function prepare(runs,getter,options={}){
  const get=typeof getter==='function'?getter:r=>r[getter];
  const perCapita=!!options.perCapita,scale=options.scale||'values';
  const series=['baseline','scenario'].map(c=>points(runs[c].rows,get,perCapita));
  let reason='';
  if(scale==='index'){
    const opening=series[0][0]?.[1];
    if(!finite(opening)||opening<=0){reason='A common index needs a known, positive opening reference value. Choose Values or Difference to inspect this series.';series.forEach(a=>a.forEach(p=>{p[1]=null;}));}
    else series.forEach(a=>a.forEach(p=>{p[1]=finite(p[1])?p[1]/opening*100:null;}));
  }
  const difference=series[1].map(([t,v],i)=>[t,finite(v)&&finite(series[0][i]?.[1])?v-series[0][i][1]:null]);
  return {series,difference,lines:scale==='difference'?[difference]:series,perCapita,scale,reason};
}
function ticks(low,high,count=4){
  if(!finite(low)||!finite(high))return [];
  if(low>high)[low,high]=[high,low];
  if(low===high){const pad=Math.max(Math.abs(low)*.05,1);low-=pad;high+=pad;}
  const rough=(high-low)/Math.max(1,count),power=10**Math.floor(Math.log10(rough)),f=rough/power;
  const step=(f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*power;
  const start=Math.floor(low/step)*step,end=Math.ceil(high/step)*step;
  return Array.from({length:Math.min(30,Math.round((end-start)/step)+1)},(_,i)=>Number((start+i*step).toPrecision(12)));
}
function path(points,X,Y){let text='',open=false;for(const [x,y] of points){if(!finite(x)||!finite(y)){open=false;continue;}text+=(open?'L':'M')+X(x).toFixed(3)+','+Y(y).toFixed(3)+' ';open=true;}return text.trim();}
function nearest(rows,t){if(!rows.length)return 0;let best=0;for(let i=1;i<rows.length;i++)if(Math.abs(rows[i].t-t)<Math.abs(rows[best].t-t))best=i;return best;}
function csv(data,metadata={}){const keys=Object.keys(metadata),rows=[['year','reference','alternative','alternative_minus_reference',...keys],...data.series[0].map(([t,b],i)=>[t,b,data.series[1][i]?.[1],data.difference[i]?.[1],...keys.map(k=>metadata[k])])];return rows.map(row=>row.map(v=>v==null?'':/[\n\r,"]/u.test(String(v))?'"'+String(v).replaceAll('"','""')+'"':v).join(',')).join('\n');}
function dimensions(parent){const style=getComputedStyle(parent),cols=style.gridTemplateColumns.split(' ').length,gap=parseFloat(style.columnGap)||0;return Math.max(180,Math.floor((parent.clientWidth-gap*(cols-1))/cols)-20);}
function create(tag,attrs={},text){const e=document.createElement(tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!=null)e.textContent=text;return e;}
function svgNode(svg,tag,attrs={},text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!=null)e.textContent=text;svg.append(e);return e;}
function download(name,body,type){const url=URL.createObjectURL(new Blob([body],{type})),a=create('a',{href:url,download:name});a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function compact(v){if(v!==0&&Math.abs(v)<.001)return v.toExponential(1);if(Math.abs(v)>=1e6)return number(v/1e6,1)+'m';if(Math.abs(v)>=1e4)return number(v/1e3,1)+'k';return number(v,Math.abs(v)<.1?3:2);}
function plot(config){
  const {title,getter,runs,frame,onInspect}=config,o=config.options||{},parent=document.getElementById(o.parent),id=(o.parent+'-'+title).replace(/[^a-zA-Z0-9]+/g,'-');
  const d=prepare(runs,getter,o),fig=create('figure',{class:'chart',id:'figure-'+id});
  fig.append(create('figcaption',{},title));
  const intrinsic=o.intrinsic,unit=d.scale==='index'?'Index · opening reference = 100':(o.unit||'Model units')+(d.perCapita?' / population-index unit':'');
  const caption=(d.scale==='difference'?'Alternative minus reference · ':'')+unit;
  fig.append(create('p',{class:'chart-unit'},caption));
  const values=d.lines.flat().filter(p=>finite(p[1]));
  if(!values.length){fig.append(create('p',{},d.reason||runs.scenario.valuation_error||'No supported values under these assumptions.'));return fig;}
  const all=values.map(p=>p[1]);if(d.scale==='difference')all.push(0);
  const yt=ticks(Math.min(...all),Math.max(...all));const low=yt[0],high=yt.at(-1);
  const W=dimensions(parent),H=W<350?250:270,L=Math.max(44,Math.min(80,Math.max(...yt.map(v=>(compact(o.mode==='pct'?v*100:v)+(o.mode==='pct'?' pp':'')).length*7.1+12)))),R=15,T=24,B=42;
  const minT=runs.baseline.rows[0].t,maxT=runs.baseline.rows.at(-1).t;
  const X=t=>L+(t-minT)/(maxT-minT||1)*(W-L-R),Y=v=>T+(high-v)/(high-low)*(H-T-B);
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  for(const[k,v]of Object.entries({viewBox:`0 0 ${W} ${H}`,role:'img',tabindex:0,'data-chart-id':id,'aria-label':title+'. '+caption+'. Click or use Left and Right arrows to inspect a year.','aria-describedby':'reading-'+id}))svg.setAttribute(k,v);
  svgNode(svg,'title',{},title);svgNode(svg,'desc',{},caption+'. Dashed reference and solid alternative. Gaps indicate unsupported values.');
  const shockNotes=[];
  for(const [i,s]of (o.shocks||[]).entries()){
    const start=Math.max(minT,s.start),end=Math.min(maxT,s.shape==='step'?maxT:s.end);
    if(end<=start||start>maxT)continue;
    svgNode(svg,'rect',{x:X(start),y:T,width:X(end)-X(start),height:H-T-B,fill:'#f2f2f2','data-shock':i+1});
    for(const t of [start,end])svgNode(svg,'line',{x1:X(t),x2:X(t),y1:T,y2:H-B,stroke:'#888','stroke-dasharray':'2 4','stroke-width':.6});
    shockNotes.push((s.shape==='ramp'?'Ramp builds':s.shape==='pulse'?'Pulse active':'Step active')+' '+number(s.start)+'–'+number(s.shape==='step'?maxT:s.end));
  }
  const axisValue=v=>compact(o.mode==='pct'?v*100:v)+(o.mode==='pct'?(d.scale==='difference'?' pp':'%'):'');
  for(const v of yt){svgNode(svg,'line',{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:v===0?'#000':'#ccc','stroke-width':v===0?1:.6});svgNode(svg,'text',{x:L-7,y:Y(v)+5,'text-anchor':'end'},axisValue(v));}
  const times=[minT,...ticks(minT,maxT,W<350?2:4).filter(t=>t>minT&&t<maxT&&X(t)-X(minT)>32&&X(maxT)-X(t)>32),maxT];
  for(const t of times){svgNode(svg,'line',{x1:X(t),x2:X(t),y1:H-B,y2:H-B+4,stroke:'black'});svgNode(svg,'text',{x:X(t),y:H-B+20,'text-anchor':'middle'},number(t,2));}
  svgNode(svg,'text',{x:(L+W-R)/2,y:H-1,'text-anchor':'middle'},'Year');
  svgNode(svg,'line',{x1:L,x2:L,y1:T,y2:H-B,stroke:'black'});
  const legend=create('div',{class:'chart-legend'});
  (d.scale==='difference'?['Alternative − reference']:['Reference','Alternative']).forEach((name,i)=>{const label=create('span');label.append(create('span',{class:'line-swatch '+(d.scale!=='difference'&&i===0?'dashed':'solid'),'aria-hidden':'true'}),document.createTextNode(name));legend.append(label);});
  const readValue=v=>!finite(v)?'Unavailable':(o.mode==='pct'?number(v*100)+'%':number(v));
  const readDifference=v=>!finite(v)?'Unavailable':signed(o.mode==='pct'?v*100:v)+(o.mode==='pct'?' pp':d.scale==='index'?' index points':'');
  const reading=create('p',{class:'chart-reading',id:'reading-'+id});
  const textAt=i=>'Year '+number(d.series[0][i][0])+': reference '+readValue(d.series[0][i][1])+' · alternative '+readValue(d.series[1][i][1])+' · difference '+readDifference(d.difference[i][1])+'.';
  reading.textContent=textAt(Math.min(frame,d.series[0].length-1));
  const selectedX=X(runs.scenario.rows[frame].t);
  svgNode(svg,'line',{x1:selectedX,x2:selectedX,y1:T,y2:H-B,stroke:'black','stroke-dasharray':'3 4','stroke-width':1,'data-selected-year':runs.scenario.rows[frame].t});
  d.lines.forEach((a,i)=>{svgNode(svg,'path',{d:path(a,X,Y),fill:'none',stroke:'black','stroke-width':i===0&&d.scale!=='difference'?1.7:2.3,'stroke-dasharray':i===0&&d.scale!=='difference'?'7 5':'none','vector-effect':'non-scaling-stroke','data-series':i});const p=a[frame];if(p&&finite(p[1]))svgNode(svg,'circle',{cx:X(p[0]),cy:Y(p[1]),r:4,fill:i===0&&d.scale!=='difference'?'white':'black',stroke:'black','stroke-width':1.5});});
  const hover=svgNode(svg,'line',{x1:0,x2:0,y1:T,y2:H-B,stroke:'#777','stroke-width':.8,visibility:'hidden'});
  const pointerFrame=e=>{const rect=svg.getBoundingClientRect(),x=(e.clientX-rect.left)*W/rect.width;return nearest(runs.scenario.rows,minT+(Math.max(L,Math.min(W-R,x))-L)/(W-L-R)*(maxT-minT));};
  svg.addEventListener('pointermove',e=>{const i=pointerFrame(e),x=X(runs.scenario.rows[i].t);hover.setAttribute('x1',x);hover.setAttribute('x2',x);hover.setAttribute('visibility','visible');reading.textContent=textAt(i);});
  svg.addEventListener('pointerleave',()=>{hover.setAttribute('visibility','hidden');reading.textContent=textAt(frame);});
  svg.addEventListener('click',e=>onInspect(pointerFrame(e),id));
  svg.addEventListener('keydown',e=>{const targets={ArrowLeft:frame-1,ArrowRight:frame+1,Home:0,End:runs.scenario.rows.length-1};if(e.key in targets){e.preventDefault();onInspect(Math.max(0,Math.min(runs.scenario.rows.length-1,targets[e.key])),id);}});
  fig.append(legend,svg,reading);
  if(shockNotes.length)fig.append(create('p',{class:'chart-note'},'Shaded: '+[...new Set(shockNotes)].join('; ')+'.'+((o.shocks||[]).some(s=>s.shape==='ramp')?' Ramp shading marks the build, then the setting holds.':'')));
  if(intrinsic)fig.append(create('p',{class:'chart-note'},intrinsic));
  const detail=create('details',{class:'chart-data'}),summary=create('summary',{},'Data and export');detail.append(summary);
  detail.addEventListener('toggle',()=>{if(!detail.open||detail.childElementCount>1)return;
    detail.append(create('p',{},caption+'. Axes expand to the displayed data. Missing values remain gaps.'),create('p',{},d.perCapita?'Per capita = numerator / each path’s population index. Population is uncalibrated; these are not currency amounts per actual resident.':'No population division is applied to this chart.'));
    const tools=create('div',{class:'toolbar'}),dataButton=create('button',{},'Download data'),svgButton=create('button',{},'Download SVG');
    dataButton.addEventListener('click',()=>download(id+'.csv',csv(d,{unit:d.scale==='index'?'index; opening reference = 100':o.mode==='pct'?'fraction':o.unit||'Model units',source_unit:o.unit||'Model units',basis:d.perCapita?'per population-index unit':'native denominator',scale:d.scale}),'text/csv'));
    svgButton.addEventListener('click',()=>{
      const clone=svg.cloneNode(true),exportW=Math.max(W,640);clone.removeAttribute('tabindex');clone.removeAttribute('aria-describedby');clone.setAttribute('xmlns','http://www.w3.org/2000/svg');clone.setAttribute('viewBox',`0 0 ${exportW} ${H+112}`);clone.setAttribute('width',exportW);clone.setAttribute('height',H+112);
      for(const text of clone.querySelectorAll('text'))text.setAttribute('style','font:14.667px "Times New Roman",Times,serif;fill:black');
      const group=document.createElementNS(svg.namespaceURI,'g');while(clone.firstChild)group.append(clone.firstChild);group.setAttribute('transform',`translate(${(exportW-W)/2} 90)`);
      svgNode(clone,'rect',{x:.5,y:.5,width:exportW-1,height:H+111,fill:'white',stroke:'black'});clone.append(group);
      const style='font:14.667px "Times New Roman",Times,serif;fill:black';
      svgNode(clone,'text',{x:12,y:21,style},title);svgNode(clone,'text',{x:12,y:41,style},caption);
      svgNode(clone,'text',{x:12,y:61,style},(d.scale==='difference'?'Solid: alternative minus reference · selected year ':'Reference: dashed · alternative: solid · selected year ')+number(runs.scenario.rows[frame].t));
      svgNode(clone,'text',{x:12,y:81,style},d.perCapita?'Population is an uncalibrated index; not currency per actual resident.':'Original illustrative model · all rights reserved');
      download(id+'.svg',new XMLSerializer().serializeToString(clone),'image/svg+xml');
    });
    tools.append(dataButton,svgButton);detail.append(tools);
    const scroller=create('div',{class:'table-scroll'}),table=create('table'),head=create('thead'),body=create('tbody'),tr=create('tr');
    for(const name of ['Year','Reference','Alternative','Difference'])tr.append(create('th',{scope:'col'},name));head.append(tr);table.append(head,body);
    d.series[0].forEach(([t,b],i)=>{const row=create('tr');for(const value of [number(t),readValue(b),readValue(d.series[1][i][1]),readDifference(d.difference[i][1])])row.append(create('td',{},value));body.append(row);});scroller.append(table);detail.append(scroller);
  });fig.append(detail);return fig;
}
function phase(config){
  const{title,xget,yget,runs,frame}=config,o=config.options||{},fig=create('figure',{class:'chart'});
  fig.append(create('figcaption',{},title),create('p',{class:'chart-unit'},'Horizontal: '+o.xLabel+' · vertical: '+o.yLabel));
  const paths=['baseline','scenario'].map(c=>runs[c].rows.map(r=>[xget(r),yget(r)])),valid=paths.flat().filter(p=>p.every(finite));
  if(!valid.length){fig.append(create('p',{},'No supported pair under these assumptions.'));return fig;}
  const xt=ticks(Math.min(...valid.map(p=>p[0])),Math.max(...valid.map(p=>p[0])),3),yt=ticks(Math.min(...valid.map(p=>p[1])),Math.max(...valid.map(p=>p[1])),3);
  const W=dimensions(document.getElementById(o.parent)),H=270,L=55,R=20,T=22,B=40,X=v=>L+(v-xt[0])/(xt.at(-1)-xt[0])*(W-L-R),Y=v=>T+(yt.at(-1)-v)/(yt.at(-1)-yt[0])*(H-T-B);
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');for(const[k,v]of Object.entries({viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':title+'. Horizontal '+o.xLabel+'. Vertical '+o.yLabel}))svg.setAttribute(k,v);
  for(const v of yt){svgNode(svg,'line',{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:'#ccc','stroke-width':.6});svgNode(svg,'text',{x:L-7,y:Y(v)+5,'text-anchor':'end'},compact(v));}
  for(const v of xt)svgNode(svg,'text',{x:X(v),y:H-12,'text-anchor':'middle'},compact(v));
  svgNode(svg,'path',{d:`M${L},${T}V${H-B}H${W-R}`,fill:'none',stroke:'black'});
  paths.forEach((a,i)=>{svgNode(svg,'path',{d:path(a,X,Y),fill:'none',stroke:'black','stroke-width':i?2.3:1.7,'stroke-dasharray':i?'none':'7 5'});const p=a[frame];if(p?.every(finite))svgNode(svg,'circle',{cx:X(p[0]),cy:Y(p[1]),r:4,fill:i?'black':'white',stroke:'black'});});
  fig.append(svg,create('p',{},'Year '+number(runs.scenario.rows[frame].t)+': reference ('+paths[0][frame].map(v=>number(v)).join(', ')+'); alternative ('+paths[1][frame].map(v=>number(v)).join(', ')+').'),create('p',{class:'chart-note'},'Dashed reference; solid alternative. Points mark the shared selected year. Phase plots retain their stated axes; display controls transform time charts. This joint path is not an estimated causal relationship.'));return fig;
}
return {divide,points,prepare,ticks,path,nearest,csv,plot,phase};
});
