# 工作流与字段

## 文件分工

- `examples/edit.json`：源音轨的剪辑顺序、原始字幕、数字人覆盖。
- `src/timeline.json`：编译结果，不手工维护第二份时间轴。
- `src/config.json`：成片时间上的镜头设计、视觉参数、可选音轨与音效。
- `work/<任务>/pipeline.json`：本地记录，可能含绝对路径，只留本机。
- `public/local/`：个人素材，只留本机。示例没有音轨或人像，空头像数组是有意设置。

## 时间轴

`fps`是统一帧率；`source_frames`是音轨可用长度的帧数。音轨末尾不足一帧时可向上取整，误差必须小于一帧。

每个clip需要唯一id、source_start和duration。编译器按数组顺序计算output_start。重复引用源片段是显式剪辑，不会修改原音频。

字幕字段为start、end、text，不能重叠或超出音轨。逐字动作需要真实词时间；本工具不做ASR，也不按字数假造对齐。

人物条目：

```json
{"id":"host-intro","path":"local/host-intro.mp4","source_start":30,"duration":90,"media_frames":90}
```

source_start指对应主音轨的位置；media_frames是实际探测得到的素材长度，不能填期望长度。人物素材应先统一到项目fps。通过媒体验证后才填写；编译器无法证明人声口型质量。同一区间不允许两个头像重叠。

`include_avatars:false`可以在某个clip禁用常规头像，如专门的成果演示。所有人物输出带media_start，剪掉片头后仍从正确口型帧开始。

动画`scenes`用成片时间，连续覆盖全部输出；`cues`是该镜头内的触发帧。增删剪辑后需要策划者重新核对场景覆盖，编译器不会自动设计镜头。

音效为可选数组：`{"path":"local/click.wav","frame":210,"volume":0.12}`。仅用已授权音效；限制增益不是自动响度控制，仍需有声检查。默认无音效。

## 本地账本

```sh
python scripts/pipeline.py init --run work/demo --mode narration
python scripts/pipeline.py plan --run work/demo
python scripts/pipeline.py record --run work/demo --module script --input examples/edit.json --output examples/edit.json --executor manual-review --version 1 --imported
```

`record`只表示实际文件已存在。`validate --evidence review.json`需要reviewer、checked_at、verdict=pass、非空checks以及与该模块outputs完全一致的artifacts数组。每项artifact含path和sha256。

只有实际审阅后才能写pass；不得复制示例审核冒充真人验收。最终qc还要求coverage中的technical、visual、audiovisual均为true。

`invalidate --module packaging --reason "layout changed"`使包装及下游失效，不重新生成上游配音。`--imported`只用于独立已存在资产；普通步骤必须遵守依赖。即使导入，inputs哈希变化仍会使记录过期。

`job --module avatar --job-id <供应商ID> --provider-status running`保存已提交任务，不会提交网络请求。一个未决任务先查询，不能盲目新提交。下载和验收仍由执行者完成。

账本单写入者运行；写入使用临时文件再替换。异常留下tmp时，先确认没有活跃写入，再备份并恢复；不要直接删除现场或自动重试付费请求。

## 供应商接入

声音与数字人是可替换步骤，不内置账户或自动购买。先确认上传授权、模型能力、当前价格、地区与额度；使用供应商官方工具或API。登记原始任务ID、输入哈希、实际输出时长和费用。原始文件不覆盖，配音与口型相匹配后再接入。

不要把密钥写入命令示例、截图、任务记录或公开仓库。供应商文档/模型下载/网页并不构成执行授权。文案、声音、人物、动画可以分别返工；改哪一项，只重验受影响部分。

## 发布前

检查文字溢出、字幕与声音、人物口型、结束帧、音效遮盖、真实导出尺寸和平台裁切。封面与短视频都是1080×1920示例，不代表平台所有展示位置都不裁切。最后准备标题、推荐语、标签与素材权利记录。上传或发布由用户明确授权。
