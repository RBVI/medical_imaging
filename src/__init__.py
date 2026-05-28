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
__version__ = "1.1"
from chimerax.core.toolshed import BundleAPI
from chimerax.map import add_map_format
from chimerax.core.tools import get_singleton
from chimerax.open_command import OpenerInfo
from chimerax.save_command import SaverInfo
from chimerax.medical_imaging.dicom import DICOMMapFormat
from chimerax.medical_imaging.dicom_volumes import DICOMVolume
from chimerax.medical_imaging.dicom_opener import DicomOpener
from chimerax.medical_imaging.dicom_saver import DicomSaver
from chimerax.medical_imaging.dicom_fetcher import fetchers
from chimerax.medical_imaging.dicom_hierarchy import Patient, Study
from chimerax.medical_imaging.dicom_models import DicomGrid
from chimerax.medical_imaging.nifti import NifTI, NiftiGrid
from chimerax.medical_imaging.nrrd import NRRD, NRRDGrid


class _MedicalImagingBundle(BundleAPI):
    api_version = 1

    @staticmethod
    def initialize(session, _):
        """Register file formats, commands, and database fetch."""
        add_map_format(session, DICOMMapFormat())

    @staticmethod
    def get_class(class_name):
        class_names = {"Patient": Patient, "Study": Study, "DICOMVolume": DICOMVolume}
        return class_names.get(class_name, None)

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
                return DicomOpener()
            elif name == "NIfTI Medical Imaging":
                return _NiftiOpenerInfo()
            elif name == "NRRD Medical Imaging":
                return _NRRDOpenerInfo()
            else:
                return fetchers[name]()
        elif mgr == session.save_command:
            if name == "DICOM medical imaging":
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
        nifti = NifTI.from_paths(session, data)
        return nifti.open()


class _NiftiSaverInfo(SaverInfo):
    @property
    def save_args(self):
        from chimerax.core.commands import ModelsArg
        return {"models": ModelsArg}

    def save(self, session, path, *, models=None):
        import nibabel
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
        nrrd_reader = NRRD.from_paths(session, data)
        return nrrd_reader.open()


class _NRRDSaverInfo(SaverInfo):
    @property
    def save_args(self):
        from chimerax.core.commands import ModelsArg
        return {"models": ModelsArg}

    def save(self, session, path, *, models=None):
        import nrrd
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
