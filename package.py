name = "libpng"

authors = [
    "Cosmin Truta",
    "Guy Eric Schalnat",
    "Andreas Dilger",
    "Glenn Randers-Pehrson",
]

version = "1.6.29"

description = \
    """
    PNG reference library
    """

with scope("config") as c:
    # Determine location to release: internal (int) vs external (ext)

    # NOTE: Modify this variable to reflect the current package situation
    release_as = "ext"

    # The `c` variable here is actually rezconfig.py
    # `release_packages_path` is a variable defined inside rezconfig.py

    import os
    if release_as == "int":
        c.release_packages_path = os.environ["SSE_REZ_REPO_RELEASE_INT"]
    elif release_as == "ext":
        c.release_packages_path = os.environ["SSE_REZ_REPO_RELEASE_EXT"]

requires = [
]

private_build_requires = [
]

variants = [
    ["platform-linux", "arch-x86_64", "os-centos-7"]
]

tools = [
]


def pre_build_commands():
    command("source /opt/rh/devtoolset-6/enable")

def commands():
    env.PNG_ROOT = "{root}"
    env.PNG_LOCATION = "{root}"
    env.PATH.append("{root}/bin")

uuid = "repository.libpng"