/* All rights reserved. Written permission required. See LICENSE. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const C=require('../charts.js');
const close=(a,b,tol=1e-10)=>assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
const fixture=(b,s)=>({baseline:{rows:b},scenario:{rows:s}});
test('a larger economy can have lower output per capita',()=>{
 const runs=fixture([{t:0,y:100,labour:100},{t:1,y:150,labour:200}],[{t:0,y:100,labour:100},{t:1,y:150,labour:200}]);
 const totals=C.prepare(runs,'y',{scale:'index'}),perCapita=C.prepare(runs,'y',{perCapita:true,scale:'index'});
 assert.equal(totals.series[1][1][1],150);assert.equal(perCapita.series[1][1][1],75);
});
test('each path uses its own population, with a common reference index',()=>{
 const runs=fixture([{t:0,y:100,labour:100},{t:1,y:120,labour:100}],[{t:0,y:100,labour:200},{t:1,y:120,labour:150}]);
 const d=C.prepare(runs,'y',{perCapita:true,scale:'index'});assert.deepEqual(d.series[1],[[0,50],[1,80]]);close(d.difference[1][1],-40);
});
test('price and population adjustment are distinct and path-specific',()=>{
 const runs=fixture([{t:0,income:200,price:2,labour:100}],[{t:0,income:600,price:3,labour:400}]);
 const d=C.prepare(runs,r=>r.income/r.price,{perCapita:true});close(d.series[0][0][1],1);close(d.series[1][0][1],.5);
});
test('missing, zero or invalid population produces a gap without a fallback',()=>{
 for(const labour of [undefined,null,0,-1,NaN,Infinity])assert.equal(C.prepare(fixture([{t:0,y:1,labour:100}],[{t:0,y:1,labour}]),'y',{perCapita:true}).series[1][0][1],null);
});
test('missing valuations remain unavailable and do not become zero wealth',()=>{
 for(const y of [undefined,null,NaN,Infinity])assert.equal(C.prepare(fixture([{t:0,y:100,labour:100}],[{t:0,y,labour:100}]),'y',{perCapita:true}).series[1][0][1],null);
});
test('losses and negative net wealth are preserved in values and differences',()=>{
 const d=C.prepare(fixture([{t:0,y:-10,labour:10}],[{t:0,y:-20,labour:10}]),'y',{perCapita:true,scale:'difference'});
 assert.equal(d.series[1][0][1],-2);assert.equal(d.lines[0][0][1],-1);
});
test('zero or negative opening reference cannot silently create an index',()=>{
 for(const y of [0,-1,null]){const d=C.prepare(fixture([{t:0,y}],[{t:0,y:2}]),'y',{scale:'index'});assert.ok(d.reason);assert.equal(d.series[1][0][1],null);}
});
test('transforms do not mutate stored economic data',()=>{
 const runs=fixture([{t:0,y:10,labour:2}],[{t:0,y:20,labour:4}]),before=JSON.stringify(runs);C.prepare(runs,'y',{perCapita:true,scale:'index'});assert.equal(JSON.stringify(runs),before);
});
test('line paths stop at missing values rather than bridging the gap',()=>{const p=C.path([[0,1],[1,2],[2,null],[3,4]],x=>x,y=>y);assert.equal((p.match(/M/g)||[]).length,2);assert.equal((p.match(/L/g)||[]).length,1);assert.ok(!p.includes('NaN'));});
test('readable ticks enclose positive, negative, tiny and constant ranges',()=>{
 for(const [low,high]of [[0,1],[-300,-20],[-.0003,.0004],[5,5],[0,0],[1e8,2e8]]){const a=C.ticks(low,high);assert.ok(a[0]<=low&&a.at(-1)>=high);assert.ok(a.length>=2&&a.length<=30);assert.ok(a.every(Number.isFinite));for(let i=1;i<a.length;i++)assert.ok(a[i]>a[i-1]);}
});
test('year inspection chooses the nearest calculated frame and handles endpoints',()=>{const rows=[{t:0},{t:.125},{t:.25}];assert.equal(C.nearest(rows,.13),1);assert.equal(C.nearest(rows,-1),0);assert.equal(C.nearest(rows,2),2);});
test('chart data export retains gaps and both cases',()=>{
 const d=C.prepare(fixture([{t:0,y:10},{t:1,y:12}],[{t:0,y:10},{t:1,y:null}]),'y');assert.ok(C.csv(d).endsWith('1,12,,'));assert.ok(C.csv(d).startsWith('year,reference,alternative,alternative_minus_reference'));assert.ok(C.csv(d,{unit:'real units, per year',basis:'population index'}).includes('"real units, per year"'));assert.ok(C.csv(d,{unit:'index'}).split('\n')[1].endsWith(',index'));
});
test('all saved-example per-capita output frames satisfy the level identity',()=>{
 const text=fs.readFileSync(require('node:path').join(__dirname,'../initial.js'),'utf8'),runs=JSON.parse(text.replace(/^window\.ECONOMY_INITIAL=/,'').replace(/;\s*$/,'')).result;
 const d=C.prepare(runs,'real_gdp',{perCapita:true});for(const [j,key]of ['baseline','scenario'].entries())runs[key].rows.forEach((r,i)=>close(d.series[j][i][1]*r.labour,r.real_gdp));
});
