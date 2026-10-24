# gostfetch

Distro logo on the left (auto-detected: Debian, Fedora, Arch and derivatives),
live monitoring on the right: CPU, RAM, GPU, network.

```
gostfetch                       # run
gostfetch --refresh 0.5         # update every 0.5 s
gostfetch --logo fedora         # force a logo (auto | debian | fedora | arch | none | /path/to/logo.txt)
```

Keys: `q` quit, `+`/`-` refresh speed, `l` cycle logo, `s` save to config.

## Config

`~/.config/gostfetch/config.toml` (or `$XDG_CONFIG_HOME/gostfetch/config.toml`):

```toml
refresh = 1.0    # seconds, 0.2 .. 10
logo = "auto"    # auto | debian | fedora | arch | none | /path/to/logo.txt
```

Custom logos: put `<name>.txt` into `~/.config/gostfetch/logos/`.

## Dependencies

| Package | Why |
|---|---|
| python >= 3.11 | runtime (`tomllib`, `curses`) |
| fastfetch | distro logos |
| pciutils | `lspci`, GPU name |

GPU load/VRAM: AMD is read from sysfs (nothing to install); NVIDIA uses `nvidia-smi`,
which ships with the NVIDIA driver (`nvidia-utils`) you already have if you run NVIDIA.

## Install

Arch (AUR): `yay -S gostfetch` (once published).

From source: `pip install .`

## License

MIT, see `LICENSE`.
