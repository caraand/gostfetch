#!/usr/bin/env bash
# Local test build of the AUR package, no GitHub tag needed.
# Usage:  ./packaging/arch/local-build.sh            # build only + namcap
#         ./packaging/arch/local-build.sh --install  # build, namcap, then install (makepkg -i)
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
ver="$(grep -m1 '^version' "$repo/pyproject.toml" | cut -d'"' -f2)"
work="$(mktemp -d)"
echo ">> repo: $repo"
echo ">> version: $ver"
echo ">> build dir: $work"

# tarball shaped like a GitHub release: top directory gostfetch-<ver>/
tar czf "$work/gostfetch-$ver.tar.gz" \
  --transform "s|^\.|gostfetch-$ver|" \
  --exclude=.git --exclude=__pycache__ --exclude=dist --exclude=build \
  --exclude='*.egg-info' --exclude=packaging \
  -C "$repo" .

# real PKGBUILD, with source pointed at the local tarball
sed 's|^source=.*|source=("gostfetch-$pkgver.tar.gz")|' \
  "$repo/packaging/arch/PKGBUILD" > "$work/PKGBUILD"

cd "$work"
echo ">> namcap PKGBUILD"
namcap PKGBUILD || true

echo ">> makepkg"
if [[ "${1:-}" == "--install" ]]; then
  makepkg -sf --noconfirm
else
  makepkg -sf
fi

echo ">> namcap package"
namcap ./*.pkg.tar.zst || true

if [[ "${1:-}" == "--install" ]]; then
  sudo pacman -U ./*.pkg.tar.zst
fi

# keep a copy next to the sources (/tmp gets wiped on reboot)
mkdir -p "$repo/dist"
cp -f "$work"/*.pkg.tar.zst "$repo/dist/"
echo ">> done. package copied to:"
ls -1 "$repo"/dist/*.pkg.tar.zst
echo ">> install later with:  sudo pacman -U $repo/dist/<file>.pkg.tar.zst"
