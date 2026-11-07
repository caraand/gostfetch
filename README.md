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

Arch (AUR): `yay -S gostfetch` (once published). The package pulls in `fastfetch`.

From source: `pip install .` and install `fastfetch` with your package manager.

## License

MIT, see `LICENSE`.
