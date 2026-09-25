import React from 'react';
import {AbsoluteFill,Audio,Composition,OffthreadVideo,Sequence,interpolate,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import timeline from './timeline.json';
import rawConfig from './config.json';

type Scene={start:number;end:number;kind:string;title:string;items:string[];cues:number[]};
type Config={title:string;subtitle:string;narration:string|null;soundEffects:{path:string;frame:number;volume:number}[];theme:{background:string;surface:string;ink:string;primary:string;accent:string};scenes:Scene[]};
const config:Config=rawConfig;
const localPath=(p:string)=>{if(!p || p.startsWith('/') || p.includes('..') || /[:\\]/.test(p))throw Error('Use relative media paths inside public, not URLs or local absolute paths');return staticFile(p);};
let end=0;
for(const s of config.scenes){
 if(!Number.isInteger(s.start)||!Number.isInteger(s.end)||s.start!==end||s.end<=s.start||s.end>timeline.duration)throw Error('Scenes must cover output timeline without gaps or overlaps');
 if(!['merge','steps','retain'].includes(s.kind)||s.items.length!==3||s.cues.length!==3||s.title.length>22||s.items.some(x=>x.length>10))throw Error('Split long text into another scene; do not shrink it');
 if(s.cues.some((x,i)=>!Number.isInteger(x)||x<0||x>=s.end-s.start||(i>0&&x<s.cues[i-1])))throw Error('Invalid scene cue');
 end=s.end;
}
if(end!==timeline.duration)throw Error('Scenes must cover the complete output');
for(const fx of config.soundEffects)if(fx.volume<0||fx.volume>0.3||fx.frame<0||fx.frame>=timeline.duration)throw Error('Invalid sound effect timing or level');
const T=config.theme;
const ease=(f:number,start:number,duration=16)=>interpolate(f,[start,start+duration],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
const Icon=({kind}:{kind:number})=><svg width="90" height="90" viewBox="0 0 90 90" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">{kind===0?<><rect x="17" y="14" width="56" height="62" rx="10"/><circle cx="45" cy="35" r="10"/><path d="M28 65q17-28 34 0"/></>:kind===1?<>{[20,30,40,50,60,70].map((x,i)=><path key={x} d={`M${x} ${22+i%3*6}v${46-i%3*12}`}/>)}</>:<><rect x="10" y="18" width="70" height="50" rx="9"/><path d="m39 31 18 12-18 12zM30 78h30"/></>}</svg>;
const SceneView=({scene:s}:{scene:Scene})=>{const f=useCurrentFrame();const joined=ease(f,s.cues[2],22);return <AbsoluteFill>
 <div style={{position:'absolute',left:82,right:90,top:255,fontSize:66,fontWeight:750,lineHeight:1.2}}>{s.title}</div>
 {s.items.map((text,i)=>{const a=ease(f,s.cues[i]);const isMerge=s.kind==='merge';const x=isMerge?(i===0?90+joined*55:i===1?570-joined*55:250):105;
 const y=isMerge?(i===2?960:570):(510+i*265);const scale=s.kind==='retain'&&i===2?1+Math.sin(Math.PI*a)*0.09:1;
 return <div key={i} style={{position:'absolute',left:x,top:y+(1-a)*28,width:isMerge?(i===2?560:330):805,height:isMerge?235:210,borderRadius:30,boxSizing:'border-box',padding:30,background:T.surface,border:`2px solid ${i===2?T.primary:'#E9DFF5'}`,color:i===1?T.accent:T.primary,boxShadow:'0 14px 35px #30104C0C',opacity:a,transform:`scale(${scale})`,display:'flex',alignItems:'center',gap:24,flexDirection:isMerge?'column':'row'}}><Icon kind={i}/><span style={{fontSize:36,fontWeight:650,color:T.ink}}>{text}</span>{s.kind==='retain'&&i<2&&a>0.9?<span style={{marginLeft:'auto',fontSize:30,color:T.accent}}>✓</span>:null}</div>;})}
 {s.kind==='merge'?<svg style={{position:'absolute',top:820,left:250}} width="570" height="120"><path d="M20 0 Q20 65 285 65 Q550 65 550 0 M285 65 V115" fill="none" stroke={T.primary} strokeWidth="4" strokeDasharray="700" strokeDashoffset={700*(1-joined)}/></svg>:null}
 </AbsoluteFill>;};
const Film=()=>{const f=useCurrentFrame();const cap=timeline.captions.find(c=>f>=c.start&&f<c.end);return <AbsoluteFill style={{background:T.background,color:T.ink,fontFamily:'Arial, Microsoft YaHei, sans-serif'}}>
 <div style={{position:'absolute',left:44,right:44,top:170,bottom:260,background:'#FFFFFF99',borderRadius:44}}/>
 <div style={{position:'absolute',left:82,top:95,fontSize:24,letterSpacing:4,color:T.primary}}>EXPLAINER / WORKFLOW</div>
 {config.scenes.map(s=><Sequence key={s.start} from={s.start} durationInFrames={s.end-s.start}><SceneView scene={s}/></Sequence>)}
 {config.narration?timeline.clips.map(c=><Sequence key={c.id} from={c.output_start} durationInFrames={c.duration}><Audio src={localPath(config.narration!)} startFrom={c.source_start}/></Sequence>):null}
 {(timeline.avatars as {id:string;path:string;start:number;duration:number;media_start:number}[]).map((a,i)=><Sequence key={i} from={a.start} durationInFrames={a.duration}><div style={{position:'absolute',left:85,top:1350,width:190,height:190,borderRadius:'50%',overflow:'hidden',border:'5px solid white'}}><OffthreadVideo muted src={localPath(a.path)} startFrom={a.media_start} style={{width:'100%',height:'100%',objectFit:'cover'}}/></div></Sequence>)}
 {config.soundEffects.map((fx,i)=><Sequence key={i} from={fx.frame}><Audio src={localPath(fx.path)} volume={fx.volume}/></Sequence>)}
 <div style={{position:'absolute',left:310,right:110,top:1450,fontSize:40,lineHeight:1.4}}>{cap?.text}</div>
 <div style={{position:'absolute',left:85,right:110,bottom:210,height:5,background:'#DFD2EF'}}><div style={{width:`${100*(f+1)/timeline.duration}%`,height:5,background:T.primary}}/></div>
 {!config.narration?<div style={{position:'absolute',left:85,bottom:150,fontSize:23,color:'#806C92'}}>无声布局示例 · 请换入已授权素材</div>:null}
 </AbsoluteFill>;};
const Cover=()=> <AbsoluteFill style={{background:T.background,color:T.ink,padding:90,fontFamily:'Arial, Microsoft YaHei, sans-serif'}}><div style={{fontSize:32,color:T.primary,marginTop:200}}>EXPLAINER VIDEO WORKFLOW</div><div style={{fontSize:106,fontWeight:800,lineHeight:1.2,marginTop:70}}>{config.title}</div><div style={{fontSize:38,marginTop:65}}>{config.subtitle}</div><div style={{marginTop:140,padding:65,borderRadius:45,background:T.surface,display:'flex',gap:70,color:T.primary}}><Icon kind={0}/><Icon kind={1}/><Icon kind={2}/></div><div style={{fontSize:34,marginTop:70}}>先看效果，再保存成模板</div></AbsoluteFill>;
registerRoot(()=> <><Composition id="Explainer" component={Film} durationInFrames={timeline.duration} fps={timeline.fps} width={1080} height={1920}/><Composition id="Cover" component={Cover} durationInFrames={1} fps={30} width={1080} height={1920}/></>);
