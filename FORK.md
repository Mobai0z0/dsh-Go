# 本仓库说明

本仓库是 [ccch1mneyyy/dsh-go](https://github.com/ccch1mneyyy/dsh-go) 的 fork，用来做鸿蒙（HarmonyOS / OpenHarmony）适配与发布。Android 版本的功能开发、打包和分发都在上游仓库，本仓库不重复做。

## 和上游的关系

| 事 | 怎么做 |
|---|---|
| 同步上游代码 | `.github/workflows/sync-upstream.yml` 每 6 小时把上游默认分支合进本仓库的 `main`：本仓库没有自己的提交时快进，两边都动过时做一次合并，改到同一处就失败留给人处理 |
| 发版前先同步 | 发版流程把同步当第一个 job 调用（`detect` → `sync` → `aot` → …），不是靠时间错开。同步失败这一版就不发，免得用旧代码打包 |
| 同步鸿蒙分支 | 同一个 workflow 还会把 `SYNC_BRANCHES` 里的分支快进过来，默认就是上游的 `claude/harmonyos-ohos`；本仓库在这些分支上有自己的提交时不覆盖，要覆盖得手动选 `force`，设成 `-` 可以关掉额外分支同步 |
| 改上游功能 | 上游仓库提，不在 fork 里改。本仓库只放鸿蒙相关的东西 |
| 不改上游文件 | `main` 上只**新增**文件（本文件、两个 workflow、`docs/ohos-release.md`），上游已有的文件一行都不动。同步因此不会冲突：上游的 README、`docs/release.md` 改了也照常合进来，不会被本仓库的改动挡住 |
| 外部 PR | 不接收，与上游政策一致（见 [AGENTS.md](AGENTS.md)） |

## 发布什么

只发 `ohos-*` 的 GitHub Release，不发 Android APK。APK 由上游仓库的发版机器发布；鸿蒙版本由 `.github/workflows/ohos-release.yml` 在上游发新版本后自动打，规则见 [docs/ohos-release.md](docs/ohos-release.md)。

产物是 Dart AOT 那一半（`libapp.so`）；往 `ohos-toolchain` release 上传过一次原生库之后，还会自动打出**没签名**的 HAP（`dsh-go-<版本>-ohos-arm64-unsigned.hap`）。没上传就只有 AOT，不报错。

## 手动同步

网页上：仓库首页 → **Sync fork** → **Update branch**。

命令行：

```sh
gh api --method POST repos/<owner>/<repo>/merge-upstream -f branch=main
```

要在 Actions 页手动跑（可以指定额外分支或强制覆盖）：**Actions** → **Sync upstream** → **Run workflow**。

## 需要的仓库设置（只做一次）

- **Settings → Actions → General → Workflow permissions** 选 **Read and write**，否则同步和发版都建不了东西。
- 加一个仓库 secret **`SYNC_TOKEN`**：classic PAT 勾 `repo` + `workflow`，或 fine-grained PAT 给 Contents、Workflows 两项 Write。上游一改 `.github/workflows/*`，同步就会用到它——`GITHUB_TOKEN` 是 GitHub App 令牌，**永远**没有写 workflow 文件的权限，不加这个 secret 同步会卡在 `refusing to allow a GitHub App to create or update workflow`。缺这个 secret 时同步仍按 `GITHUB_TOKEN` 跑，只是碰到 workflow 改动就会失败。
- 在 **Actions** 页启用 workflow（新建的 fork 默认不跑定时任务）。
- 仓库变量一个都不用配，全有默认值：`SYNC_UPSTREAM_REPO`、`SYNC_BRANCHES`（默认 `claude/harmonyos-ohos`）、`OHOS_REF`、`OHOS_UPSTREAM_REPO`。只有要 CI 打 HAP 时才需要 `OHOS_HAP_BUILD`、`OHOS_NATIVES_URL` 和两个 secrets，见 [docs/ohos-release.md](docs/ohos-release.md)。

配好之后，上游发版 → 6 小时内自动同步、自动构建、自动发布，全程不需要点按钮。

---

# About this repository

This is a fork of [ccch1mneyyy/dsh-go](https://github.com/ccch1mneyyy/dsh-go) for HarmonyOS (OpenHarmony) work. Android feature development, packaging and distribution stay upstream; this fork does not repeat them.

- **Syncing**: `.github/workflows/sync-upstream.yml` merges the upstream default branch into `main` every 6 hours — fast-forward when the fork has no commits of its own, a merge when both sides moved, and a failure that needs a person when they touch the same lines. Branches listed in `SYNC_BRANCHES` (the HarmonyOS one, for example) are fast-forwarded too, and are never overwritten unless `force` is chosen.
- **Sync runs before a release**: the release pipeline calls this workflow as its first job (`detect` → `sync` → `aot` → …), so ordering is a job dependency, not a guess about cron minutes. If the sync fails, that release is not published rather than built from stale code.
- **Changes**: upstream changes go to the upstream repository. This fork holds HarmonyOS work only.
- **No upstream file is edited**: `main` only *adds* files (this one, the two workflows, `docs/ohos-release.md`). Upstream's own files are left untouched, so a sync cannot conflict — upstream README and `docs/release.md` changes merge in as usual.
- **External PRs**: not accepted, same policy as upstream ([AGENTS.md](AGENTS.md)).
- **Releases**: only `ohos-*` GitHub Releases, no Android APK. APKs come from the upstream release machine; HarmonyOS releases are built by `.github/workflows/ohos-release.yml` after an upstream release, see [docs/ohos-release.md](docs/ohos-release.md). The notes are the upstream changelog copied verbatim, with this fork's artifact list appended.
- **Set up once**: Workflow permissions **Read and write**, a `SYNC_TOKEN` secret, and enable the workflows on the Actions page. No repository variables are needed — all have defaults. After that, an upstream release is synced, built and published within 6 hours without any button.
- **Why `SYNC_TOKEN`**: `GITHUB_TOKEN` is a GitHub App token and never holds permission to write `.github/workflows/*`, so the first sync that carries an upstream workflow change fails with `refusing to allow a GitHub App to create or update workflow`. The secret must be a PAT — classic with `repo` + `workflow`, or fine-grained with Contents and Workflows write. Without it the sync still runs on `GITHUB_TOKEN` and only fails when a workflow file changed.
- **Artifacts**: the Dart AOT half (`libapp.so`), plus an **unsigned** HAP (`dsh-go-<version>-ohos-arm64-unsigned.hap`) once the native libraries have been uploaded to the `ohos-toolchain` release. Without that upload only the AOT ships, and nothing fails.
- **Manual sync**: the repository page's **Sync fork** button, `gh api --method POST repos/<owner>/<repo>/merge-upstream -f branch=main`, or **Actions → Sync upstream → Run workflow**.
- **Required setting**: **Settings → Actions → General → Workflow permissions** must be **Read and write**.
