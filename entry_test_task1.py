
import json
import urllib.request
import urllib.error

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version


PYTHON_VERSION = Version("3.11")


def get_pypi_data(url):
    """Fetch JSON data from PyPI."""
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "DependencyChecker/1.0"}
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        print(f"HTTP error: {error.code} for {url}")
        return None

    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Network error: {error}")
        return None


def get_minimum_python(requires_python):
    """Extract the minimum Python version requirement."""
    if not requires_python:
        return None

    specifiers = SpecifierSet(requires_python)

    minimum = None

    for spec in specifiers:
        if spec.operator in (">=", ">", "~="):
            version = Version(spec.version)

            if minimum is None or version > minimum:
                minimum = version

    return minimum


def main():
    counts = 0
    not_found = 0
    incompatible = 0

    highest_requirement = None

    with open("requirements.txt", "r") as file:
        lines = file.readlines()

    for line in lines:

        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        counts += 1

        try:
            requirement = Requirement(line)

            name = requirement.name

            # Get the pinned version
            pinned_versions = [
                spec.version
                for spec in requirement.specifier
                if spec.operator == "=="
                and "*" not in spec.version
            ]

            if len(pinned_versions) != 1:
                print(f"Unsupported requirement: {line}")
                continue

            version = pinned_versions[0]

            # Check whether the package exists
            package_url = (
                f"https://pypi.org/pypi/{name}/json"
            )

            package_data = get_pypi_data(package_url)

            if package_data is None:
                not_found += 1
                continue

            # Check whether the pinned release exists
            version_url = (
                f"https://pypi.org/pypi/{name}/{version}/json"
            )

            release_data = get_pypi_data(version_url)

            if release_data is None:
                not_found += 1
                continue

            # Read Python version requirement
            requires_python = (
                release_data["info"].get("requires_python")
            )

            if requires_python:
                supported = SpecifierSet(requires_python)

                if not supported.contains(PYTHON_VERSION):
                    incompatible += 1

            # Find the highest minimum Python requirement
            minimum = get_minimum_python(requires_python)

            if minimum is not None:

                if (
                    highest_requirement is None
                    or minimum > highest_requirement["minimum"]
                ):
                    highest_requirement = {
                        "name": name,
                        "version": version,
                        "minimum": minimum,
                        "requires_python": requires_python
                    }

        except Exception as error:
            print(f"Error processing {line}: {error}")

    print(f"Dependencies checked: {counts}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python 3.11: {incompatible}")

    if highest_requirement:
        result = highest_requirement

        print(
            f"Highest requirement: "
            f"{result['name']}=={result['version']} "
            f"({result['requires_python']})"
        )
    else:
        print("Highest requirement: None")


if __name__ == "__main__":
    main()
