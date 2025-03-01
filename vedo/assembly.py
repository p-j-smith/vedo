#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

try:
    import vedo.vtkclasses as vtk
except ImportError:
    import vtkmodules.all as vtk

import vedo

__docformat__ = "google"

__doc__ = """
Submodule for managing groups of vedo objects

![](https://vedo.embl.es/images/basic/align4.png)
"""

__all__ = ["Group", "Assembly", "procrustes_alignment"]


#################################################
def procrustes_alignment(sources, rigid=False):
    """
    Return an ``Assembly`` of aligned source meshes with the `Procrustes` algorithm.
    The output ``Assembly`` is normalized in size.

    The `Procrustes` algorithm takes N set of points and aligns them in a least-squares sense
    to their mutual mean. The algorithm is iterated until convergence,
    as the mean must be recomputed after each alignment.

    The set of average points generated by the algorithm can be accessed with
    ``algoutput.info['mean']`` as a numpy array.

    Arguments:
        rigid : bool
            if `True` scaling is disabled.

    Examples:
        - [align4.py](https://github.com/marcomusy/vedo/tree/master/examples/basic/align4.py)

        ![](https://vedo.embl.es/images/basic/align4.png)
    """

    group = vtk.vtkMultiBlockDataGroupFilter()
    for source in sources:
        if sources[0].npoints != source.npoints:
            vedo.logger.error("sources have different nr of points")
            raise RuntimeError()
        group.AddInputData(source.polydata())
    procrustes = vtk.vtkProcrustesAlignmentFilter()
    procrustes.StartFromCentroidOn()
    procrustes.SetInputConnection(group.GetOutputPort())
    if rigid:
        procrustes.GetLandmarkTransform().SetModeToRigidBody()
    procrustes.Update()

    acts = []
    for i, s in enumerate(sources):
        poly = procrustes.GetOutput().GetBlock(i)
        mesh = vedo.mesh.Mesh(poly)
        mesh.SetProperty(s.GetProperty())
        if hasattr(s, "name"):
            mesh.name = s.name
        acts.append(mesh)
    assem = Assembly(acts)
    assem.transform = procrustes.GetLandmarkTransform()
    assem.info["mean"] = vedo.utils.vtk2numpy(procrustes.GetMeanPoints().GetData())
    return assem


#################################################
class Group(vtk.vtkPropAssembly):
    """Form groups of generic objects (not necessarily meshes)."""

    def __init__(self, objects=()):
        """Form groups of generic objects (not necessarily meshes)."""

        vtk.vtkPropAssembly.__init__(self)

        self.name = ""
        self.created = ""
        self.trail = None
        self.trail_points = []
        self.trail_segment_size = 0
        self.trail_offset = None
        self.shadows = []
        self.info = {}
        self.rendered_at = set()
        self.transform = None
        self.scalarbar = None

        for a in vedo.utils.flatten(objects):
            if a:
                self.AddPart(a)

        self.PickableOff()

    def __iadd__(self, obj):
        """
        Add an object to the group
        """
        if not vedo.utils.is_sequence(obj):
            obj = [obj]
        for a in obj:
            if a:
                self.AddPart(a)
        return self

    def unpack(self):
        """Unpack the group into its elements"""
        elements = []
        self.InitPathTraversal()
        parts = self.GetParts()
        parts.InitTraversal()
        for i in range(parts.GetNumberOfItems()):
            ele = parts.GetItemAsObject(i)
            elements.append(ele)

        # gr.InitPathTraversal()
        # for _ in range(gr.GetNumberOfPaths()):
        #     path  = gr.GetNextPath()
        #     print([path])
        #     path.InitTraversal()
        #     for i in range(path.GetNumberOfItems()):
        #         a = path.GetItemAsObject(i).GetViewProp()
        #         print([a])

        return elements

    def clear(self):
        """Remove all parts"""
        for a in self.unpack():
            self.RemovePart(a)
        return self

    def on(self):
        """Switch on visibility"""
        self.VisibilityOn()
        return self

    def off(self):
        """Switch off visibility"""
        self.VisibilityOff()
        return self

    def pickable(self, value=None):
        """Set/get the pickability property of an object."""
        if value is None:
            return self.GetPickable()
        self.SetPickable(value)
        return self

    def draggable(self, value=None):
        """Set/get the draggability property of an object."""
        if value is None:
            return self.GetDragable()
        self.SetDragable(value)
        return self

    def pos(self, x=None, y=None):
        """Set/Get object position."""
        if x is None:  # get functionality
            return np.array(self.GetPosition())

        if y is None:  # assume x is of the form (x,y)
            x, y = x
        self.SetPosition(x, y)
        return self

    def shift(self, ds):
        """Add a shift to the current object position."""
        p = np.array(self.GetPosition())

        self.SetPosition(p + ds)
        return self

    def bounds(self):
        """
        Get the object bounds.
        Returns a list in format [xmin,xmax, ymin,ymax].
        """
        return self.GetBounds()

    def diagonal_size(self):
        """Get the length of the diagonal"""
        b = self.GetBounds()
        return np.sqrt((b[1] - b[0]) ** 2 + (b[3] - b[2]) ** 2)

    def show(self, **options):
        """
        Create on the fly an instance of class ``Plotter`` or use the last existing one to
        show one single object.

        This method is meant as a shortcut. If more than one object needs to be visualised
        please use the syntax `show(mesh1, mesh2, volume, ..., options)`.

        Returns the ``Plotter`` class instance.
        """
        return vedo.plotter.show(self, **options)


#################################################
class Assembly(vedo.base.Base3DProp, vtk.vtkAssembly):
    """
    Group many objects and treat them as a single new object.
    """

    def __init__(self, *meshs):
        """
        Group many objects and treat them as a single new object,
        keeping track of internal transformations.

        Examples:
            - [gyroscope1.py](https://github.com/marcomusy/vedo/tree/master/examples/simulations/gyroscope1.py)

            ![](https://vedo.embl.es/images/simulations/39766016-85c1c1d6-52e3-11e8-8575-d167b7ce5217.gif)
        """
        vtk.vtkAssembly.__init__(self)
        vedo.base.Base3DProp.__init__(self)

        if len(meshs) == 1:
            meshs = meshs[0]
        else:
            meshs = vedo.utils.flatten(meshs)

        self.actors = meshs

        if meshs and hasattr(meshs[0], "top"):
            self.base = meshs[0].base
            self.top = meshs[0].top
        else:
            self.base = None
            self.top = None

        scalarbars = []
        for a in meshs:
            if isinstance(a, vtk.vtkProp3D):  # and a.GetNumberOfPoints():
                self.AddPart(a)
            if hasattr(a, "scalarbar") and a.scalarbar is not None:
                scalarbars.append(a.scalarbar)

        if len(scalarbars) > 1:
            self.scalarbar = Group(scalarbars)
        elif len(scalarbars) == 1:
            self.scalarbar = scalarbars[0]

        self.pipeline = vedo.utils.OperationNode(
            "Assembly", parents=meshs, comment=f"#meshes {len(meshs)}", c="#f08080"
        )
        ###################################################################

    def _repr_html_(self):
        """
        HTML representation of the Assembly object for Jupyter Notebooks.

        Returns:
            HTML text with the image and some properties.
        """
        import io
        import base64
        from PIL import Image

        library_name = "vedo.assembly.Assembly"
        help_url = "https://vedo.embl.es/docs/vedo/assembly.html"

        arr = self.thumbnail(zoom=1.1, elevation=-60)

        im = Image.fromarray(arr)
        buffered = io.BytesIO()
        im.save(buffered, format="PNG", quality=100)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        url = "data:image/png;base64," + encoded
        image = f"<img src='{url}'></img>"

        # statisitics
        bounds = "<br/>".join(
            [
                vedo.utils.precision(min_x, 4) + " ... " + vedo.utils.precision(max_x, 4)
                for min_x, max_x in zip(self.bounds()[::2], self.bounds()[1::2])
            ]
        )

        help_text = ""
        if self.name:
            help_text += f"<b> {self.name}: &nbsp&nbsp</b>"
        help_text += '<b><a href="' + help_url + '" target="_blank">' + library_name + "</a></b>"
        if self.filename:
            dots = ""
            if len(self.filename) > 30:
                dots = "..."
            help_text += f"<br/><code><i>({dots}{self.filename[-30:]})</i></code>"

        allt = [
            "<table>",
            "<tr>",
            "<td>",
            image,
            "</td>",
            "<td style='text-align: center; vertical-align: center;'><br/>",
            help_text,
            "<table>",
            "<tr><td><b> nr. of objects </b></td><td>"
            + str(self.GetNumberOfPaths())
            + "</td></tr>",
            "<tr><td><b> position </b></td><td>" + str(self.GetPosition()) + "</td></tr>",
            "<tr><td><b> diagonal size </b></td><td>"
            + vedo.utils.precision(self.diagonal_size(), 5)
            + "</td></tr>",
            "<tr><td><b> bounds </b> <br/> (x/y/z) </td><td>" + str(bounds) + "</td></tr>",
            "</table>",
            "</table>",
        ]
        return "\n".join(allt)

    def __add__(self, obj):
        """
        Add an object to the assembly
        """
        if isinstance(obj, vtk.vtkProp3D):
            self.AddPart(obj)

        self.actors.append(obj)

        if hasattr(obj, "scalarbar") and obj.scalarbar is not None:
            if self.scalarbar is None:
                self.scalarbar = obj.scalarbar
                return self

            def unpack_group(scalarbar):
                if isinstance(scalarbar, Group):
                    return scalarbar.unpack()
                else:
                    return scalarbar

            if isinstance(self.scalarbar, Group):
                self.scalarbar += unpack_group(obj.scalarbar)
            else:
                self.scalarbar = Group([unpack_group(self.scalarbar), unpack_group(obj.scalarbar)])
        self.pipeline = vedo.utils.OperationNode("add mesh", parents=[self, obj], c="#f08080")
        return self

    def __contains__(self, obj):
        """Allows to use ``in`` to check if an object is in the Assembly."""
        return obj in self.actors

    def clone(self):
        """Make a clone copy of the object."""
        newlist = []
        for a in self.actors:
            newlist.append(a.clone())
        return Assembly(newlist)

    def unpack(self, i=None, transformed=False):
        """Unpack the list of objects from a ``Assembly``.

        If `i` is given, get `i-th` object from a ``Assembly``.
        Input can be a string, in this case returns the first object
        whose name contains the given string.

        Examples:
            - [custom_axes4.py](https://github.com/marcomusy/vedo/tree/master/examples/pyplot/custom_axes4.py)
        """
        if transformed:
            actors = []
            for a in self.actors:
                actors.append(a.clone(transformed=True))
        else:
            actors = self.actors

        if i is None:
            return actors
        elif isinstance(i, int):
            return actors[i]
        elif isinstance(i, str):
            for m in actors:
                if i in m.name:
                    return m

    def recursive_unpack(self):
        """Flatten out an Assembly."""

        def _genflatten(lst):
            if not lst:
                return []
            ##
            if isinstance(lst[0], Assembly):
                lst = lst[0].unpack()
            ##
            for elem in lst:
                if isinstance(elem, Assembly):
                    apos = elem.GetPosition()
                    asum = np.sum(apos)
                    for x in elem.unpack():
                        if asum:
                            yield x.clone().shift(apos)
                        else:
                            yield x
                else:
                    yield elem

        return list(_genflatten([self]))

    def pickable(self, value=None):
        """Set/get the pickability property of an assembly and its elements"""
        # set property to each element
        if value is not None:
            for elem in self.recursive_unpack():
                elem.SetPickable(value)

        # set property for self using inherited pickable()
        return super().pickable(value=value)
