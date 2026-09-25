# Dependencies and provenance

本仓库的流程代码、时间轴编译器、示例组件与SVG图标由本项目编写。示例文字为虚构教学内容，不含客户资料或人物素材。

- Remotion / @remotion/cli：通过npm安装，不打包其源码或二进制。Remotion采用其自己的许可，不能因为本项目是MIT就假定所有商业使用免费。请查看 https://www.remotion.dev/docs/license 和所安装版本的LICENSE。
- React / React DOM：MIT，安装包保留上游声明。
- TypeScript：Apache-2.0；@types/react遵从安装包许可证。
- npm传递依赖分别遵从各自许可；package-lock.json锁定版本，未将node_modules纳入发行。
- 系统字体不随仓库分发；正式交付时检查实际使用字体的许可和可用性。

制作方法曾参考以下项目；本公开发行不包含其源码、卡片、截图、音效或改写后的实现：

- https://github.com/Vincentwei1021/video-shotcraft （本地所读快照为Apache-2.0；使用该项目时自行核对所选版本）
- https://github.com/Vincentwei1021/video-talkcraft （本地所读快照为PolyForm Noncommercial 1.0.0；未纳入本MIT发行，也不默认安装）

VoxCPM、EMO等仅作为可选供应商方法说明；本包不包含模型权重、服务额度或供应商执行器。用户应自行确认其服务条款与素材使用权。
