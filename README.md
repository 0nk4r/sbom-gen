# SBOMGen

**SBOMGen** is a cross-platform command-line wrapper script that helps generate Software Bill of Materials (SBOM) either:

*  Locally using [Syft](https://github.com/anchore/syft), or
*  Remotely via GitHub's Dependency Graph API.

> ⚠️ Note: This is not a new SBOM generation engine. It's a convenience wrapper built to simplify usage of existing tools like Syft and GitHub APIs, with added UI, CSV support, and automation.

---

##  Features

* Generate SBOM from your local codebase using Syft.
* Fetch SBOM from GitHub using REST API.
* Process a single GitHub repo or batch from a CSV file.
* Output saved in SPDX JSON format.
* Rich terminal UI with themes and error handling.

---

##  Prerequisites

* Python 3.6+
* `syft` installed (for local mode): [https://github.com/anchore/syft](https://github.com/anchore/syft)
* GitHub CLI (`gh`) installed (recommended)
* GitHub Personal Access Token (with `read:packages` and `repo` scopes)

---

##  Installation

```bash
pip install -r requirements.txt
chmod +x sbomgen.py
```

---

##  Usage

### Generate SBOM Locally (Using Syft)

```bash
python sbomgen.py --local
```

###  Fetch SBOM for a Single GitHub Repo

```bash
python sbomgen.py --online --repo onkark/sample-app --token YOUR_GITHUB_TOKEN
```

###  Fetch SBOM for Multiple Repos via CSV

**Format your CSV like this (no header):**

```
onkark/repo1
someorg/repo2
```

**Then run:**

```bash
python sbomgen.py --online --file repos.csv --token YOUR_GITHUB_TOKEN
```

All SBOM files are saved to the `sboms/` directory.

---

##  GitHub Token

Make sure to use a [GitHub personal access token](https://github.com/settings/tokens) with proper permissions.

* Required scopes: `repo`, `read:packages`

Set via CLI:

```bash
--token YOUR_GITHUB_TOKEN
```

Or export to env:

```bash
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
```

---

##  Output

* All SBOMs are saved in SPDX JSON format.
* Example: `sboms/onkark_sample-app_sbom.json`

---

##  Requirements File (optional)

If you're using `rich`, add this to `requirements.txt`:

```
rich
requests
```

---

##  License

MIT License

---

##  Contribution

PRs and issues welcome! Help make SBOMGen more powerful and developer-friendly.

---

##  Author

Created by [OnkarK](https://onkark.com)
