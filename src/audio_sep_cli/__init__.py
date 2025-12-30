from importlib.metadata import PackageNotFoundError, version as _version

__all__ = ["__version__"]

try:
    __version__ = _version("audio-sep-cli")
except PackageNotFoundError:
    __version__ = "0.0.0+local"
