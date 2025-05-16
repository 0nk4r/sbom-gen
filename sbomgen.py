#!/usr/bin/env python3
import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

GITHUB_API_URL = "https://api.github.com"


def run_syft(target_path: str, output_file: Path):
    """Run syft locally to generate SBOM SPDX JSON."""
    if not Path(target_path).exists():
        console.print(f"[red]Error: Target path does not exist: {target_path}[/]")
        sys.exit(1)

    try:
        cmd = [
            "syft",
            target_path,
            "-o",
            "spdx-json",
            "-q",
            "-f",
            str(output_file),
        ]
        subprocess.run(cmd, check=True)
        console.print(f"[green]SBOM generated at {output_file}[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Syft failed with exit code {e.returncode}[/]")
        sys.exit(1)
    except FileNotFoundError:
        console.print("[red]Error: 'syft' command not found. Please install syft and ensure it's in your PATH.[/]")
        sys.exit(1)


def fetch_sbom_from_github(owner: str, repo: str, token: str, output_file: Path):
    """Fetch SBOM from GitHub Dependency Graph API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/dependency-graph/sbom"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        console.print(f"[green]SBOM saved: {output_file}[/]")
    elif response.status_code == 404:
        console.print(f"[yellow]SBOM not found for {owner}/{repo}. It may be private or unavailable.[/]")
    elif response.status_code in (401, 403):
        console.print(f"[red]Authentication failed or insufficient permissions for {owner}/{repo}.[/]")
    else:
        console.print(f"[red]Failed to fetch SBOM for {owner}/{repo}. HTTP {response.status_code}[/]")


def read_repos_from_csv(file_path: Path):
    repos = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row and row[0].strip():
                repos.append(row[0].strip())
    return repos


def read_repos_from_txt(file_path: Path):
    repos = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            repo = line.strip()
            if repo:
                repos.append(repo)
    return repos


def parse_github_repo(repo_input: str):
    """
    Accepts either:
    - owner/repo
    - full URL like https://github.com/owner/repo
    Returns (owner, repo) tuple or None if invalid.
    """
    repo_input = repo_input.strip()
    if repo_input.startswith("http://") or repo_input.startswith("https://"):
        try:
            parsed = urlparse(repo_input)
            if parsed.netloc.lower() != "github.com":
                return None
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        except Exception:
            return None
    else:
        # Assume owner/repo format
        parts = repo_input.split("/")
        if len(parts) == 2 and all(parts):
            return parts[0], parts[1]
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="SBOMGen: Generate SBOM locally via syft or fetch from GitHub Dependency Graph API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--local", action="store_true", help="Generate SBOM locally using syft")
    group.add_argument("--online", action="store_true", help="Fetch SBOM from GitHub API")

    parser.add_argument(
        "--repo",
        type=str,
        help="Single GitHub repo in 'owner/repo' format or full GitHub URL (for online mode)",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to file with list of repos (CSV or TXT) (for online mode)",
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Target path to scan (for local mode)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sboms",
        help="Output directory to save SBOM files",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub Personal Access Token (or set env var GITHUB_TOKEN)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.local:
        if not args.target:
            console.print("[red]Error: --target is required for local mode[/]")
            sys.exit(1)

        out_file = output_dir / "local_sbom.spdx.json"
        run_syft(args.target, out_file)

    else:
        if not args.repo and not args.file:
            console.print("[red]Error: Provide --repo or --file for online mode[/]")
            sys.exit(1)

        if args.token is None:
            console.print("[red]Error: GitHub token required via --token or GITHUB_TOKEN env variable[/]")
            sys.exit(1)

        repos_parsed = []

        if args.repo:
            parsed = parse_github_repo(args.repo)
            if not parsed:
                console.print(f"[red]Invalid repo format or URL: {args.repo}[/]")
                sys.exit(1)
            repos_parsed = [parsed]

        else:
            file_path = Path(args.file)
            if not file_path.exists():
                console.print(f"[red]File not found: {file_path}[/]")
                sys.exit(1)
            if file_path.suffix.lower() == ".csv":
                raw_repos = read_repos_from_csv(file_path)
            else:
                raw_repos = read_repos_from_txt(file_path)

            invalid_repos = []
            for r in raw_repos:
                parsed = parse_github_repo(r)
                if not parsed:
                    invalid_repos.append(r)
                else:
                    repos_parsed.append(parsed)

            if invalid_repos:
                console.print(f"[red]Invalid repo formats/URLs found in file: {invalid_repos}[/]")
                sys.exit(1)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("[green]Fetching SBOMs...", total=len(repos_parsed))
            for owner, repo_name in repos_parsed:
                output_file = output_dir / f"{owner}_{repo_name}_sbom.json"
                fetch_sbom_from_github(owner, repo_name, args.token, output_file)
                progress.update(task, advance=1)


if __name__ == "__main__":
    main()
