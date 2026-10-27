# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# https://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===
__version__ = "1.1.1"
from chimerax.core.toolshed import BundleAPI
from chimerax.map import add_map_format
from chimerax.core.tools import get_singleton
from chimerax.open_command import OpenerInfo
from chimerax.save_command import SaverInfo
from chimerax.medical_imaging.dicom import DICOMMapFormat

# The format descriptor is needed at startup; readers and savers are not.
_lazy_exports = {
    'DICOMVolume': ('dicom_volumes', 'DICOMVolume'),
    'DicomOpener': ('dicom_opener', 'DicomOpener'),
    'DicomSaver': ('dicom_saver', 'DicomSaver'),
    'fetchers': ('dicom_fetcher', 'fetchers'),
    'Patient': ('dicom_hierarchy', 'Patient'),
    'Study': ('dicom_hierarchy', 'Study'),
    'DicomGrid': ('dicom_models', 'DicomGrid'),
    'NifTI': ('nifti', 'NifTI'),
    'NiftiGrid': ('nifti', 'NiftiGrid'),
    'NRRD': ('nrrd', 'NRRD'),
    'NRRDGrid': ('nrrd', 'NRRDGrid'),
}
_lazy_modules = {module for module, _ in _lazy_exports.values()} | {
    'coordinates', 'errors', 'modality', 'types',
}
# Reloading the package must not leave old class exports cached.
for _name in _lazy_exports:
    globals().pop(_name, None)


def __getattr__(name):
    from importlib import import_module
    if name in _lazy_exports:
        module_name, attribute = _lazy_exports[name]
        value = getattr(import_module('.' + module_name, __name__), attribute)
    elif name in _lazy_modules:
        value = import_module('.' + name, __name__)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | _lazy_exports.keys() | _lazy_modules)



class _MedicalImagingBundle(BundleAPI):
    api_version = 1

    @staticmethod
    def initialize(session, _):
        """Register file formats, commands, and database fetch."""
        add_map_format(session, DICOMMapFormat())

    @staticmethod
    def get_class(class_name):
        if class_name in ('Patient', 'Study', 'DICOMVolume'):
            from importlib import import_module
            return getattr(import_module(__name__), class_name)
        return None

    @staticmethod
    def start_tool(session, _, ti):
        if ti.name == "DICOM Browser":
            from chimerax.medical_imaging.ui import DICOMBrowserTool

            return get_singleton(session, DICOMBrowserTool, "DICOM Browser")
        else:
            from chimerax.medical_imaging.ui import DICOMDatabases

            return get_singleton(session, DICOMDatabases, "DICOM Browser")

    @staticmethod
    def run_provider(session, name, mgr, **kw):
        # Handle open/save command providers
        if mgr == session.open_command:
            if name == "DICOM medical imaging":
                from .dicom_opener import DicomOpener
                return DicomOpener()
            elif name == "NIfTI Medical Imaging":
                return _NiftiOpenerInfo()
            elif name == "NRRD Medical Imaging":
                return _NRRDOpenerInfo()
            else:
                from .dicom_fetcher import fetchers
                return fetchers[name]()
        elif mgr == session.save_command:
            if name == "DICOM medical imaging":
                from .dicom_saver import DicomSaver
                return DicomSaver()
            elif name == "NIfTI Medical Imaging":
                return _NiftiSaverInfo()
            elif name == "NRRD Medical Imaging":
                return _NRRDSaverInfo()
        # Handle toolbar providers
        else:
            from chimerax.medical_imaging import toolbar_actions

            toolbar_actions.run_provider(session, name)


class _NiftiOpenerInfo(OpenerInfo):
    def open(self, session, data, *args, **kw):
        from .nifti import NifTI
        nifti = NifTI.from_paths(session, data)
        return nifti.open()


class _NiftiSaverInfo(SaverInfo):
    @property
    def save_args(self):
        from chimerax.core.commands import ModelsArg
        return {"models": ModelsArg}

    def save(self, session, path, *, models=None):
        import nibabel
        from .nifti import NiftiGrid
        reference_volume = models[0].reference_volume
        original_grid = reference_volume.data
        affine = None
        if isinstance(original_grid, NiftiGrid):
            affine = original_grid.nifti_data._raw_data.affine
        else:
            session.logger.warning(
                "Source data is not NIfTI; the saved segmentation will have the default rotation for NIfTI files."
            )
        img = nibabel.nifti2.Nifti2Image(models[0].data.array, affine)
        nibabel.save(img, path)


class _NRRDOpenerInfo(OpenerInfo):
    def open(self, session, data, *args, **kw):
        from .nrrd import NRRD
        nrrd_reader = NRRD.from_paths(session, data)
        return nrrd_reader.open()


class _NRRDSaverInfo(SaverInfo):
    @property
    def save_args(self):
        from chimerax.core.commands import ModelsArg
        return {"models": ModelsArg}

    def save(self, session, path, *, models=None):
        import nrrd
        from .nrrd import NRRDGrid
        import numpy as np
        reference_volume = models[0].reference_volume
        original_grid = reference_volume.data
        if not isinstance(original_grid, NRRDGrid):
            session.logger.warning(
                "Source data is not NRRD; the saved segmentation may not necessarily line up with the source data if opened again."
            )
        data = np.asfortranarray(models[0].data.array)
        nrrd.write(
            file=path,
            data=data,
            header={
                "dimension": 3,
                "sizes": models[0].data.size[::-1],
                "space origin": models[0].data.origin,
                "spacings": models[0].data.step[::-1],
                "kinds": ["domain", "domain", "domain"],
                "type": data.dtype.name,
            },
        )


bundle_api = _MedicalImagingBundle()

# Preserve wildcard exports without importing their implementations eagerly.
__all__ = sorted({name for name in globals() if not name.startswith("_")}
                 | _lazy_exports.keys() | _lazy_modules)
