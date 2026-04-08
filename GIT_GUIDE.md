# Git 使用指南

## 安装 Git

1. 下载 Git: https://git-scm.com/download/win
2. 安装时选择默认设置即可

## 初始化仓库

在项目目录中打开命令行（PowerShell 或 CMD）：

```bash
git init
```

## 添加文件到暂存区

```bash
git add .
```

## 提交更改

```bash
git commit -m "初始提交：视频快速混剪工具"
```

## 连接远程仓库

1. 在 GitHub/Gitee/GitLab 创建新仓库
2. 复制远程仓库地址
3. 添加远程仓库：

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
```

## 推送到远程仓库

```bash
git branch -M main
git push -u origin main
```

## .gitignore 说明

项目已包含 `.gitignore` 文件，会自动忽略：

- Python 缓存文件 (`__pycache__/`, `*.pyc`)
- IDE 配置 (`.vscode/`, `.idea/`)
- OS 文件 (`.DS_Store`, `Thumbs.db`)
- 构建文件 (`build/`, `dist/`)
- 缓存目录 (`cache/`, `output/`, `log/`)
- 二进制文件 (`*.exe`, `*.mp4`, `*.mkv`)

## 常用命令

```bash
# 查看状态
git status

# 查看日志
git log

# 拉取远程更新
git pull

# 推送更新
git push
```
