# gostfetch

Distro logo on the left, live monitoring on the right: CPU, RAM, GPU, network.

Logos come straight from [fastfetch](https://github.com/fastfetch-cli/fastfetch):
all 500+ built-in ones, not a hand-picked few. The accent color is taken from the
logo itself. The interface speaks English and Russian.

```
gostfetch                       # run (fastfetch picks the logo of your distro)
gostfetch --refresh 0.5         # update every 0.5 s
gostfetch --logo EndeavourOS    # any fastfetch logo, case-insensitive
gostfetch --list-logos          # print every available logo and exit
gostfetch --lang en             # interface language: auto | ru | en
```

`--logo` accepts `auto`, `none`, a fastfetch logo name, or a path to a `.txt` file.

## Keys

| Key | Action |
|---|---|
| `q` / `Esc` | quit |
| `+` / `-` | refresh speed |
| `l` / `L` | next / previous logo (auto, none, then every fastfetch logo) |
| `g` | switch language (ru / en) |
| `s` | save current settings to the config |

## Config

`~/.config/gostfetch/config.toml` (or `$XDG_CONFIG_HOME/gostfetch/config.toml`):

```toml
refresh = 1.0    # seconds, 0.2 .. 10
logo = "auto"    # auto | none | fastfetch logo name | /path/to/logo.txt
lang = "auto"    # auto (from LANG) | ru | en
```

Custom logos: put `<name>.txt` into `~/.config/gostfetch/logos/`. A file there wins
over the fastfetch logo with the same name.

## Dependencies

| Package | Why |
|---|---|
| python >= 3.11 | runtime (`tomllib`, `curses`) |
| fastfetch | **required**: source of all logos (`gostfetch --list-logos` needs it) |
| pciutils | `lspci`, GPU name |

Without fastfetch gostfetch still runs, but shows a plain placeholder instead of a
logo (neofetch is used as a last resort if it is installed).

GPU load/VRAM: AMD is read from sysfs (nothing to install); NVIDIA uses `nvidia-smi`,
which ships with the NVIDIA driver (`nvidia-utils`) you already have if you run NVIDIA.

## Install

Arch Linux, prebuilt package from the latest release (v0.3.0):

```
sudo pacman -U https://github.com/caraand/gostfetch/releases/download/v0.3.0/gostfetch-0.3.0-1-any.pkg.tar.zst
```

pacman pulls in the dependencies (`python`, `fastfetch`, `pciutils`) by itself.
An AUR package (`yay -S gostfetch`) will come later.

From source: `pip install .` and install `fastfetch` with your package manager.

## What's new in 0.3.0

- **All fastfetch logos.** Logos are taken straight from fastfetch: 500+ built-in
  ones instead of the previous three (Debian, Fedora, Arch). `auto` lets fastfetch
  pick the real logo of your distro (EndeavourOS, Mint, ...) instead of the nearest
  of three. New: `--logo NAME`, `--list-logos`, `l` / `L` to browse them, and the
  accent color is now read from the logo itself.
- **English and Russian interface.** `--lang auto|ru|en`, `lang` in the config,
  `g` to switch on the fly; `auto` follows `LANG`. Everything is translated:
  panels, status line, errors, `--help`.
- **fastfetch is now a required dependency** (the Arch package depends on it).
- **Sturdier logo loading.** Helper processes no longer touch the terminal input,
  and non-ASCII logos work in the C locale.

Existing configs keep working; `lang` is simply added the next time you press `s`.

## License

MIT, see `LICENSE`.
