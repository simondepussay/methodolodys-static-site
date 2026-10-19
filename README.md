# Methodolodys — WordPress → static site

ディスレクシアなど「Dys」の子ども向け無料教材サイトを、WordPressから静的サイトへ移行 / Migrating a free learning-resources site for children with dyslexia from WordPress to a static site

**https://thankful-pebble-0daf47300.4.azurestaticapps.net** (test version · テスト版)

> このリポジトリはコードのみです。教材・文章・画像は作者 Martine Jiménez さんのものなので含めていません。
> *Code only. The teaching material, texts and images belong to their author, Martine Jiménez, and are not included.*

---

## 概要 / Overview

[methodolodys.ch](https://methodolodys.ch) はスイスの特別支援教育の先生が10年かけて作った教材サイトです（無料ダウンロードのPDF・PowerPoint・Word、1 900点以上）。WordPress + Divi で動いていましたが、古いPHP、更新されないプラグイン、遅いページが問題でした。中身を一つも失わずに、軽くて安全な静的サイトに作り直しました。

*methodolodys.ch is a site built over 10 years by a special-needs teacher in Switzerland: more than 1,900 free PDFs, PowerPoints and Word files. It ran on WordPress + Divi, with an outdated PHP, abandoned plugins and slow pages. I rebuilt it as a light, secure static site without losing a single resource.*

```
WordPressのバックアップ (.wpress, 12 GB) / WordPress backup
   │  outils/extraire.py   アーカイブとMySQLダンプを読み、Diviのショートコードを解析
   │                       reads the archive and MySQL dump, parses Divi shortcodes
   ▼
site/data/ressources.json  1 920 resources · 63 pages (titles, texts, images, videos, files)
   │  outils/generer_pages.py   HTML pages · 71 redirects · 404 · sitemap
   ▼
Azure Static Web Apps (Free)          Azure Blob Storage
   HTML · CSS · JavaScript    ──────▶  1 909 files · 5.3 GB
   (no framework, no server)    links  public read · cached 1 day
```

## なぜ作り直したか / Why rebuild it

| | 旧サイト / Old (WordPress) | 新サイト / New (static) |
|---|---|---|
| サーバーの処理時間 / Server time per page | 1.1 – 1.5 s | ~7 ms |
| ページのHTML / Page HTML (compressed) | 33 KB | 1 – 3 KB |
| 動作環境 / Runtime | PHP + MySQL versions past end of life | none — static files |
| プラグイン / Plugins | 7, some no longer maintained, updates pending | 0 |
| 管理画面 / Admin login | hundreds of failed logins (brute force) | no login to attack |

*Measured from Tokyo with curl (median of 5, connection time removed), October 2026. Security points come from the site's own security-plugin logs in the backup; details are left out while the old site is still online.*

## 技術的なポイント / Technical choices

- **データを失わない移行 / Lossless migration** — `.wpress` アーカイブとMySQLダンプを直接読み、Diviのショートコード（blurb, button, toggle, video…）を順番どおりに解析。リンク切れ、文字化けしたファイル名（`Pre╠üsent` → `Présent`）、2つのURLがくっついたリンクも自動で修復。*Reads the archive and SQL dump directly and parses Divi shortcodes in page order; repairs broken links, mojibake file names and glued URLs.*
- **ストレージとページを分離 / Files apart from pages** — 5.3 GBのファイルはBlob Storage、サイト本体は16 MBだけ（Static Web Apps無料プランの上限250 MBに余裕で収まる）。*The 5.3 GB of files live in Blob Storage; the site itself is only 16 MB.*
- **データから作るページ / Data-driven pages** — 1つのJSONから、テーマ・ページ・検索・プレビューをすべて生成。フレームワークなし。*One JSON file drives themes, pages, search and previews; no framework.*
- **Dysの人のための読みやすさ / Built for dyslexic readers** — OpenDyslexicフォント、文字サイズ、行間をワンクリックで変更（選んだ人だけフォントを読み込む）。*One-click OpenDyslexic font, text size and spacing; the font loads only for those who pick it.*
- **古いURLを守る / Old links keep working** — WordPressのURL 71件を301リダイレクト。古いPDFへの直接リンクはBlob Storageへ転送。*71 WordPress URLs are 301-redirected; old direct PDF links are forwarded to Blob Storage.*
- **検証 / Verification** — 公開前に、全ページの内部リンク・画像（3 000件以上）と、全1 909ファイルのダウンロードをスクリプトで確認。*Every internal link, image and all 1,909 downloads are checked by script before publishing.*

## 使い方 / Usage

```bash
cd outils
python3 extraire.py          # backup → site/data/ressources.json + WebP previews
python3 generer_pages.py     # HTML pages, staticwebapp.config.json, 404, sitemap
python3 copier_azure.py      # files to upload → azure/
az storage blob upload-batch -d fichiers -s ../azure --account-name <account>
npx @azure/static-web-apps-cli deploy ../site --deployment-token <token> --env production
```

Python 3 (standard library + Pillow), `cwebp`, macOS `sips` / `qlmanage` for previews.

## 作り方 / How it was built

Claude Code（AIコーディングエージェント）と一緒に作りました。移行の方針、ページの構成、何を残して何を直すか、公開の判断は私が決め、毎回ブラウザで確認しました。

*Built with Claude Code, an AI coding agent. I decided the migration plan, the page structure, what to keep and what to fix, checked every change in the browser and made the publishing decisions.*
