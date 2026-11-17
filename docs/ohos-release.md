# 鸿蒙（OHOS）发版

本仓库是 [ccch1mneyyy/dsh-go](https://github.com/ccch1mneyyy/dsh-go) 的 fork，只发布鸿蒙版本。Android 的 APK 由上游的发布机器发出（上游 `docs/release.md` 那几节），本仓库不重复做，也不改动上游的任何发布配置。

> 这篇文档只存在于本仓库。它和 [FORK.md](../FORK.md) 一样是新增文件，上游没有同名文件，所以自动同步永远不会碰到它；上游 `docs/release.md` 保持原样，不会被本仓库改写。

## 流程

`.github/workflows/ohos-release.yml` 在上游发版之后自动发布鸿蒙版本。

| 项 | 约定 |
|---|---|
| 触发 | 每 6 小时查一次上游（默认 `ccch1mneyyy/dsh-go`）最新 release，和本仓库已有的 `ohos-` tag 比对；也可以在 Actions 页手动运行并指定上游 tag |
| tag | `ohos-` + 上游 tag，例如上游 `v1.2.0` → 本仓库 `ohos-v1.2.0` |
| 不重建 | 同一个 tag 已经完整就跳过；只有资产不全（上传中断）时会补齐，不重打。要重发必须换上游版本名，与 APK 的规则一致 |
| 预发布 | 上游是预发布时，本仓库这一版也标 prerelease |
| 产物 | `dsh-go-<版本>-ohos-arm64-libapp.so`、`SHA256SUMS`；这一版打过 HAP 时再加 `dsh-go-<版本>-ohos-arm64-unsigned.hap` |

五个 job：

| job | runner | 做什么 |
|---|---|---|
| `detect` | ubuntu | 选上游版本，判断这一版是否已经发过 |
| `sync` | — | 调用 `.github/workflows/sync-upstream.yml`，先把上游代码和构建分支同步到最新 |
| `aot` | macOS | 用 oh-flutter 3.47.9-ohos 编出 `libapp.so` |
| `hap` | ubuntu | 有 `ohos-toolchain` release 时打 **unsigned** HAP；失败不影响发布 |
| `publish` | ubuntu | 唯一写入的 job：建 `ohos-<上游 tag>` release |

**发版全程不签名**：不需要签名材料、不需要任何 secret 来签名，`check-arkts.sh` 也不传 `--distribution`，产物就是 `dsh-go-<版本>-ohos-arm64-unsigned.hap`。要装到手机上的签名由使用者自己做，不在这个 workflow 里。

**顺序**：`detect` → `sync` → `aot` → `hap` → `publish`，靠 job 依赖固定，不是靠时间错开。

- 发版前一定先同步：`aot` 检出的 `main` 是 `sync` 刚处理过的分支，不会拿上一次定时同步留下的旧代码打包。
- 同步失败就停：`sync` 出错（比如 `main` 冲突）时 `aot` 不会跑，这一版直接不发 —— 发旧代码比红一次更糟。
- 定时同步仍保留（每 6 小时），所以没发版的时候代码也在跟上游走；发版时那次同步通常已经没有新东西要拉。
- 检出的是**代码分支**，版本号不跟它走：HAP 的 `versionName` 由 `--version` 写入（就是这一版的发布版本），见下面「版本与设备类型」。以前默认检出 `claude/harmonyos-ohos`，那个分支的 `pubspec.yaml` 停在 1.0.16，于是每一版打出来的 HAP 都报 1.0.16。

## 产物

每次发版都有：

| 文件 | 说明 |
|---|---|
| `dsh-go-<版本>-ohos-arm64-libapp.so` | Dart AOT 那一半 |
| `SHA256SUMS` | 上面这个的校验 |

上传过一次原生库之后，还会多一个：

| 文件 | 说明 |
|---|---|
| `dsh-go-<版本>-ohos-arm64-unsigned.hap` | **没签名**的 HAP，装不到华为手机 |

## HAP 是怎么自动打出来的

用 `tooling/ohos/check-arkts.sh --full`，全程公开工具，不需要华为账号：

| 输入 | 从哪来 |
|---|---|
| OpenHarmony 公开 SDK 26.0.0.38 | 自动下载（7.0-Release 的 `ohos-sdk-windows_linux-public.tar.gz`，3.1 GB），按 sha256 校验，按摘要缓存，第二次以后不再下 |
| hvigor 6.26.9 + 插件 | `check-arkts.sh` 自己从公开 registry 取，带 sha512 校验 |
| JDK 17 / Node 24.22.1 | `setup-java` / `setup-node` |
| `libapp.so` + `flutter_assets` | 上一个 job（macOS 编译）的产物 |
| Node 头文件 | 自动下载 `node-v24.22.1.tar.gz` |
| **`libnode.so`、`libdsh_flock.so`、`libdsh_require_builtin.so`、`dsh-runtime.zip`** | **要你上传一次**，见下 |

原生库不能自动生成：`runtime/ohos/native/build-hap-libs.py` 需要先自建 clang（`build-runtimes.py`）再交叉编译整个 Node 24（`build-node.py`），耗时以小时计，放进每次发版不现实。所以它放在本仓库一个固定的 `ohos-toolchain` release 里，CI 每次直接取。

## 版本与设备类型

版本和设备类型写在 `app/ohos/AppScope/app.json5` 和 `app/ohos/entry/src/main/module.json5` 里，但打包时会重写，只认下面这几条：

| 项 | 谁写 | 规则 |
|---|---|---|
| `versionName` | `tooling/ohos/hap-version.py` | 发版时是 `--version <这一版>`（等于 release 名和资产名里的版本）；本地 `build-hap.sh` 用 `app/pubspec.yaml` 的版本 |
| `versionCode` | 同上 | 由版本号算：`major*1000000 + minor*10000 + patch*100`（1.0.16 → 1001600，1.1.0 → 1010000，预发布再减 1 排在正式版之前）。**不能用 pubspec 的 `+N`**：那个占位一直是 1，系统只装 versionCode 比已装更高的包，等于每次都是同版本 |
| `deviceTypes` | `check-arkts.sh` | 源码写 `["phone", "tablet"]`（上架要求，华为的检测项明确说 `default` 不支持上架）；但公开的 OpenHarmony SDK 只接受 `default`，所以编译时临时改成 `default`，HAP 打出来后把成品 `module.json` 里的 `default` 改回 `phone`。`audit-hap.py` 会检查成品里有没有 `phone`，缺了这次运行算失败 |

## 一次性准备原生库

在准备好的机器上（Linux 或 Intel macOS，能跑 `build-hap-libs.py` 的环境）：

```sh
# 1. 原生库：输出是一个 arm64-v8a/ 目录
python3 runtime/ohos/native/build-hap-libs.py ... --output out/arm64-v8a

# 2. 运行时：输出是一个 Stored 的 dsh-runtime/runtime.zip
python3 runtime/ohos/package/compose-runtime.py ... -o out/dsh-runtime.zip

# 3. 打成两个资产，上传成一个固定 tag 的 release
cd out && zip -r hap-libs.zip arm64-v8a && cd ..
gh release create ohos-toolchain --repo <owner>/<repo> \
  out/hap-libs.zip out/dsh-runtime.zip \
  --title "OHOS toolchain" \
  --notes "CI 打 HAP 用的原生库和运行时，不是应用版本；删掉它 HAP 就发不出来。"
```

具体参数（`--sdk-native`、`--clang`、`--cxx-runtime`、`--libnode-output`、`--node-source` 等）见 `runtime/ohos/native/build-hap-libs.py --help` 和 `app/ohos/README.md`。

**约定**：tag 固定 `ohos-toolchain`，资产名固定 `hap-libs.zip`（zip 里含 `libnode.so` 即可，有没有外层 `arm64-v8a/` 目录都行）和 `dsh-runtime.zip`。tag 或名字不一致，CI 就找不到。

## HAP 打不出来会怎样

| 情况 | 结果 |
|---|---|
| 没有 `ohos-toolchain` release | 跳过打包，release 只有 AOT，绿色通过，不是失败 |
| SDK 下载/解包失败、hvigor 报错、磁盘不够 | 同样只是这一版没 HAP，`hap` job 是 `continue-on-error`；下一轮定时会重试同一版本 |
| 想立刻重试 | Actions → OHOS release → Run workflow；已发过的 tag 若资产齐全不会重跑，所以要重打先删掉那个 release 的 HAP 资产 |

## 变量

都有默认值，不配也能跑。要改时放 Settings → Secrets and variables → Actions → Variables：

| 变量 | 默认 | 作用 |
|---|---|---|
| `OHOS_REF` | `main` | 检出哪个分支来编译（`app/ohos` 和 `tooling/ohos` 已在 `main` 上）；改回旧分支会让 HAP 的代码和版本一起停在那个分支上 |
| `OHOS_UPSTREAM_REPO` | `ccch1mneyyy/dsh-go` | 跟随的上游仓库 |
| `OHOS_SDK_URL` | 华为云 7.0-Release 的 SDK 包 | 换 SDK 来源时用 |
| `OHOS_SDK_SHA256` | 上面那个包的 sha256 | 换 SDK 来源时必须一起改 |

不需要任何 secret。

> 例外：发版流程开头的同步会用到 `SYNC_TOKEN`（见下方「一次性设置」）。发版本身不需要。

## 一次性设置

要 HAP 一共三步；不要 HAP 只做前两步。

1. **Settings → Actions → General → Workflow permissions** 选 **Read and write** —— 建 release、推同步分支都要它；设成只读两个 workflow 都会失败。
2. 加仓库 secret **`SYNC_TOKEN`**：classic PAT 勾 `repo` + `workflow`，或 fine-grained PAT 给 Contents、Workflows 两项 Write（[FORK.md](../FORK.md) 有同样一条）。上游一改 `.github/workflows/*`，同步只能用这个令牌写过去；`GITHUB_TOKEN` 无论如何都写不了。
3. 打开 **Actions** 页，把被禁用的 workflow 启用（新建的 fork 默认不跑定时任务）。
4. **上传一次原生库**到 `ohos-toolchain` release，见上面「一次性准备原生库」。不做这步就只有 AOT，没有 HAP。

仓库变量**一个都不用配**：`OHOS_REF`、`OHOS_UPSTREAM_REPO`、`SYNC_BRANCHES`、SDK 地址全有默认值；除了同步用的 `SYNC_TOKEN`，也不需要任何 secret。

## 之后会发生什么（不需要你操作）

上游一发新版本：

```
每 6 小时探测 → 找到新 tag → 同步（main + 构建分支）→ 编译 AOT → 打 HAP（有 toolchain 时）→ 发布 ohos-<tag>
```

- 全自动，不点任何按钮。release 直接发布，不是草稿。
- **构建失败**：不留下任何 release，下一次定时（6 小时内）自动重试同一版本。
- **上传中断**：release 存在但资产不全时，下一次会自动补齐（覆盖同名资产 + 重写说明），不重建整版。
- **同步冲突**：会挡一次发版并报错，解决后下一次自动继续；按 [FORK.md](../FORK.md) 的约定（只新增文件、不改上游文件）本来不会冲突。
- 手动运行 **Actions → OHOS release → Run workflow** 可以立刻发一版；勾 `dry_run` 只构建不发布。

## release 说明

说明以上游那一版的更新日志为主体，**原样搬运**（上游 `docs/changelog.md` 里的中文、English 两节都在），只在最前面加一行「对应上游版本」的链接，末尾加本仓库的产物清单和 `SHA256SUMS`。上游更新日志怎么写，这里就长什么样，本仓库不重写、不摘编。

## 前置条件

- 构建用的是 `main`（`OHOS_REF` 可改）：`app/ohos` 和 `tooling/ohos` 已经在 `main` 上，`sync` 每 6 小时把上游合进来，发版前还会再同步一次。检出别的分支时，代码和 `pubspec.yaml` 的版本都会停在那个分支上。
