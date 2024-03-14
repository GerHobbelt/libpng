name = "libpng"

authors = [
    "Cosmin Truta",
    "Guy Eric Schalnat",
    "Andreas Dilger",
    "Glenn Randers-Pehrson",
]

version = "1.6.43.sse.1.0.0"

description = \
    """
    PNG reference library
    """

with scope("config") as c:
    import os
    c.release_packages_path = os.environ["SSE_REZ_REPO_RELEASE_EXT"]

requires = [
]

private_build_requires = [
]

variants = [
]

tools = [
]

uuid = "repository.libpng"

def pre_build_commands():

    info = {}
    with open("/etc/os-release", 'r') as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue
            line_info = line.replace('\n', '').split('=')
            if len(line_info) != 2:
                continue
            info[line_info[0]] = line_info[1].replace('"', '')
    linux_distro = info.get("NAME", "centos")
    print("Using Linux distro: " + linux_distro)

    if linux_distro.lower().startswith("centos"):
        command("source /opt/rh/devtoolset-6/enable")
    elif linux_distro.lower().startswith("rocky"):
        pass

def commands():
    # NOTE: REZ package versions can have ".sse." to separate the external
    # version from the internal modification version.
    split_versions = str(version).split(".sse.")
    external_version = split_versions[0]
    internal_version = None
    if len(split_versions) == 2:
        internal_version = split_versions[1]

    env.LIBPNG_VERSION = external_version
    env.LIBPNG_PACKAGE_VERSION = external_version
    if internal_version:
        env.LIBPNG_PACKAGE_VERSION = internal_version

    env.PNG_ROOT = "{root}"
    env.PNG_LOCATION = "{root}"
    env.PATH.append("{root}/bin")

    if building:
        env.CMAKE_MODULE_PATH.append("{root}/cmake")
