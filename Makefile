# ChimeraX Medical Imaging Bundle Makefile

BUNDLE_NAME = ChimeraX-MedicalImaging

.PHONY: wheel install clean

wheel:
	pip wheel --no-deps -w dist .

install:
	pip install .

clean:
	rm -rf build dist *.egg-info src/*.egg-info
