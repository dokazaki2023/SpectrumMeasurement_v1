import csv
import gzip
import os
from math import asin, atan2, cos, degrees, hypot, sin, sqrt
import numpy as np
import pyqtgraph as pg
from pyqtgraph import Point
from pyqtgraph.Qt import QtCore, QtGui


class GlassDB:
    """
    Database of dispersion coefficients for Schott glasses + Corning 7980
    """
    def __init__(self):
        path = os.path.dirname(__file__)
        fh = gzip.open(os.path.join(path, 'schott_glasses.csv.gz'), 'rb')
        r = csv.reader(map(str, fh.readlines()))
        lines = [x for x in r]
        self.data = {}
        header = lines[0]
        for l in lines[1:]:
            info = {}
            for i in range(1, len(l)):
                info[header[i]] = l[i]
            self.data[l[0]] = info
        self.data['Corning7980'] = {   ## Thorlabs UV fused silica--not in schott catalog.
            'B1': 0.68374049400,
            'B2': 0.42032361300,
            'B3': 0.58502748000,
            'C1': 0.00460352869,
            'C2': 0.01339688560,
            'C3': 64.49327320000,
        }
        self.data['CaF2'] = {   ## Malitson (1963)
            'B1': 0.5675888,
            'B2': 0.4710914,
            'B3': 3.8484723,
            'C1': 0.050263605**2,
            'C2': 0.1003909**2,
            'C3': 34.649040**2,
        }
        self.data['ZnSe'] = {   ## Connolly (1979)
            'B1': 4.45813734,
            'B2': 0.467216334,
            'B3': 2.89566290,
            'C1': 0.200859853**2,
            'C2': 0.391371166**2,
            'C3': 47.1362108**2,
        }
        
        for k in self.data:
            self.data[k]['ior_cache'] = {}
            
    def ior(self, glass, wl):
        """
        Return the index of refraction for *glass* at wavelength *wl*.
        The *glass* argument must be a key in self.data.
        """
        info = self.data[glass]
        cache = info['ior_cache']
        if wl not in cache:
            B = list(map(float, [info['B1'], info['B2'], info['B3']]))
            C = list(map(float, [info['C1'], info['C2'], info['C3']]))
            w2 = (wl/1000.)**2
            n = sqrt(1.0 + (B[0]*w2 / (w2-C[0])) + (B[1]*w2 / (w2-C[1])) + (B[2]*w2 / (w2-C[2])))
            cache[wl] = n
        return cache[wl]
            
GLASSDB = GlassDB()

def wlPen(wl,WL_min,WL_max):
    """
    Creates and returns a QPen object with a color corresponding to the wavelength (wl) of light.
    The color is determined based on the wavelength's position within a specified range (WL_min to WL_max),
    interpolating its hue within the visible spectrum.

    Parameters:
    - wl: The wavelength of the light in nanometers.
    - WL_min: The minimum wavelength in the range of interest.
    - WL_max: The maximum wavelength in the range of interest.

    Returns: A QPen object with the calculated color and a preset width.
    """
    l1 = 4000
    l2 = 5000
    l1 = WL_min+50
    l2 = WL_max-50
        
    hue = np.clip(((l2-l1) - (wl-l1)) * 0.8 / (l2-l1), 0, 0.8)
    val = 1.0
    if wl > l2:
        val = 1.0 * (((l2-wl)/l2) + 1)
    elif wl < l1:
        val = wl * 1.0/l1
    #print hue, val
    color = pg.hsvColor(hue, 1.0, val)
    pen = pg.mkPen(color, width=1)
    return pen

class ParamObj(object):
    """
    A helper class for managing parameters of an object. 
    It provides methods to set and get parameters and to notify when a parameter state has changed. 
    This class is designed to be inherited by other classes that require dynamic parameter management.
    
    このクラスは、オブジェクトの動的なパラメータを管理するための基本クラスです。オブジェクトが持つパラメータの設定、更新、取得のための柔軟なメカニズムを提供します。このクラスは、一連のパラメータを管理し、
    パラメータ値の変更に応答する必要がある他のクラスによって継承されることを意図して設計されています。
    - `__init__`メソッドでは、パラメータを格納するための空の辞書を初期化します。
    - `__setitem__`を使用すると、辞書の構文を使用してパラメータを設定できます。
    - `setParam`メソッドは、個々のパラメータを更新するための簡略化された方法を提供します。
    - `setParams`メソッドは、複数のパラメータを一度に更新するための主要な方法です。このメソッドは、パラメータの更新時にカスタム動作を提供するためにサブクラスによってオーバーライドされることがあります。
    - `paramStateChanged`は、パラメータ値が変更されるたびに呼び出されるプレースホルダーメソッドです。サブクラスは、パラメータが変更されたときにアクションを実行するためにこのメソッドをオーバーライドできます。
    - `__getitem__`を使用すると、辞書の構文を使用してパラメータにアクセスできます。
    - `getParam`メソッドを使用して、パラメータの値を取得できます。
    """
    def __init__(self):
        # Initialize an empty dictionary to store parameters
        self.__params = {}
    
    def __setitem__(self, item, val):
        # Allows parameters to be set using dictionary syntax
        self.setParam(item, val)
        
    def setParam(self, param, val):
        # Set a single parameter. This method simplifies updating individual parameters
        self.setParams(**{param:val})
        
    def setParams(self, **params):
        """
        Update multiple parameters at once. 
        This method is the primary way of updating parameters of the object 
        and can be overridden by subclasses to provide custom behavior upon parameter updates.
        """
        self.__params.update(params)
        self.paramStateChanged()

    def paramStateChanged(self):
        # A placeholder method that is called whenever parameter values change.
        # Subclasses can override this method to perform actions when parameters change.
        pass

    def __getitem__(self, item):
        # Allows parameters to be accessed using dictionary syntax
        return self.getParam(item)  
    
    def __len__(self):
        # Provides a workaround for a specific bug in PySide
        return 0

    def getParam(self, param):
        # Retrieve the value of a parameter
        return self.__params[param]

class Optic(pg.GraphicsObject, ParamObj):
    """
    Represents an optical element within the simulation. 
    This class combines the graphical representation capabilities of pg.GraphicsObject 
    with the dynamic parameter management of ParamObj, allowing for the flexible simulation of optical elements.

    Attributes:
    - sigStateChanged: 
    A signal that is emitted whenever an optical parameter changes, 
    allowing for responsive updates to the simulation or UI.

    Methods:
    - updateTransform: 
    Adjusts the graphical representation of the optic based on its parameters, 
    such as position and angle, ensuring that the visual representation matches the simulated state.
    - setParam and setParams: 
    Inherited from ParamObj, these methods allow for dynamic updating of parameters like position, angle, and other optical properties.
    - roiChanged: 
    Handles changes to the region of interest (ROI), updating the optic's parameters accordingly.
    """
    sigStateChanged = QtCore.Signal()
    
    def __init__(self, name,  gitem, **params):
        """
        Initializes the optical element with a name, graphical representation, and parameters.
        
        Parameters:
        - name: The name of the optical element.
        - gitem: The graphical item associated with this optic.
        - params: A dictionary of parameters specific to the optic.
        """
        ParamObj.__init__(self)
        pg.GraphicsObject.__init__(self) #, [0,0], [1,1])
        self.gitem = gitem
        self.surfaces = gitem.surfaces
        gitem.setParentItem(self)
        
        self.name = name
        self.roi = pg.ROI([0,0], [1,1])
        self.roi.addRotateHandle([1, 1], [0.5, 0.5])
        self.roi.setParentItem(self)
        
        defaults = {
            'pos': Point(0,0),
            'angle': 0,
        }
        
        defaults.update(params)
        self._ior_cache = {}
        self.roi.sigRegionChanged.connect(self.roiChanged)
        self.setParams(**defaults)
        
    def updateTransform(self):
        """
        Updates the optic's transformation based on its parameters (e.g., position, angle).
        This method should be called after any change in the optic's parameters that would
        affect its graphical representation.
        """
        self.setPos(0, 0)
        tr = QtGui.QTransform()
        self.setTransform(tr.translate(Point(self['pos'])).rotate(self['angle']))
        
    def setParam(self, param, val):
        """
        Sets a specific parameter for the optic. 
        Overrides ParamObj.setParam to ensure any changes are applied to the graphical representation as well.
        
        Parameters:
        - param: The name of the parameter to set.
        - val: The value to set for the parameter.
        """
        ParamObj.setParam(self, param, val)

    def paramStateChanged(self):
        """
        Called when any parameter of the optic changes. 
        This method can be overridden by subclasses to perform custom actions 
        in response to parameter changes, such as updating the simulation.
        """
        self.gitem.setPos(Point(self['pos']))
        self.gitem.resetTransform()
        self.gitem.setRotation(self['angle'])
        
        # Move ROI to match
        try:
            self.roi.sigRegionChanged.disconnect(self.roiChanged)
            br = self.gitem.boundingRect()
            o = self.gitem.mapToParent(br.topLeft())
            self.roi.setAngle(self['angle'])
            self.roi.setPos(o)
            self.roi.setSize([br.width(), br.height()])
        finally:
            self.roi.sigRegionChanged.connect(self.roiChanged)
        print('{} is moved to {} with the angle of {:.1f} degree.\n'.format(self.name,self['pos'],self['angle']))
        self.sigStateChanged.emit()

    def roiChanged(self, *args):
        """
        Handles changes to the optic's Region of Interest (ROI). 
        Updates the optic's parameters based on the new ROI settings.
        
        Parameters:
        - args: Additional arguments, not used in this base implementation but may be used in subclasses.
        """
        pos = self.roi.pos()
        # rotate gitem temporarily so we can decide where it will need to move
        self.gitem.resetTransform()
        self.gitem.setRotation(self.roi.angle())
        br = self.gitem.boundingRect()
        o1 = self.gitem.mapToParent(br.topLeft())
        self.setParams(angle=self.roi.angle(), pos=pos + (self.gitem.pos() - o1))
        
    def boundingRect(self):
        return QtCore.QRectF()
        
    def paint(self, p, *args):
        pass

    def ior(self, wavelength):
        return GLASSDB.ior(self['glass'], wavelength)

class Lens(Optic):
    def __init__(self, **params):
        defaults = {
            'dia': 25.4,  ## diameter of lens
            'r1': 50.,    ## positive means convex, use 0 for planar
            'r2': 0,   ## negative means convex
            'd': 4.0,
            'glass': 'N-BK7',
            'reflect': False,
            'name':'Lens'
        }
        defaults.update(params)
        d = defaults.pop('d')
        defaults['x1'] = -d/2.
        defaults['x2'] = d/2.
        self.name = defaults.pop('name')
        gitem = CircularSolid(brush=(100, 100, 130, 100), **defaults)
        Optic.__init__(self, self.name, gitem, **defaults)
        
    def propagateRay(self, ray):
        """Refract, reflect, absorb, and/or scatter ray. This function may create and return new rays"""
        iors = [self.ior(ray['wl']), 1.0]
        for i in [0,1]:
            surface = self.surfaces[i]
            ior = iors[i]
            p1, ai = surface.intersectRay(ray)
            if p1 is None:
                ray.setEnd(None)
                break
            p1 = surface.mapToItem(ray, p1)      
            rd = ray['dir']
            a1 = atan2(rd[1], rd[0])

            try:
                ar = a1 - ai + asin((sin(ai) * ray['ior'] / ior))
            except ValueError:
                ar = np.nan
            ray.setEnd(p1)
            dp = Point(cos(ar), sin(ar))
            ray = Ray(parent=ray, ior=ior, dir=dp)
        return [ray]

class Mirror(Optic):
    def __init__(self, **params):
        defaults = {
            'r1': 0,
            'r2': 0,
            'd': 0.01,
            'name':'Mirror'
        }
        defaults.update(params)
        d = defaults.pop('d')
        defaults['x1'] = -d/2.
        defaults['x2'] = d/2.
        self.name = defaults.pop('name')
        gitem = CircularSolid(brush=(100,100,100,255), **defaults)
        Optic.__init__(self, self.name, gitem, **defaults)
        
    def propagateRay(self, ray):
        """
        Refract, reflect, absorb, and/or scatter ray. 
        This function may create and return new rays.
        """
        surface = self.surfaces[0]
        p1, ai = surface.intersectRay(ray)
        if p1 is not None:
            p1 = surface.mapToItem(ray, p1)
            rd = ray['dir']
            ray.setEnd(p1)
            a1 = atan2(rd[1], rd[0])
            ar = a1 + np.pi - 2 * ai
            dp = Point(cos(ar), sin(ar))
            ray = Ray(parent=ray, dir=dp)
        else:
            ray.setEnd(None)
        return [ray]

class Grating(Optic):
    def __init__(self, **params):
        defaults = {
            'r1': 0,
            'r2': 0,
            'd': 0.01,
            'Groove':300,
            'name':'Grating'
        }
        defaults.update(params)
        d = defaults.pop('d')
        defaults['x1'] = -d/2.
        defaults['x2'] = d/2.
        self.pitch = 1000/defaults.pop('Groove')
        self.name = defaults.pop('name')
        gitem = CircularSolid(brush=(100,100,100,255), **defaults)
        Optic.__init__(self, self.name, gitem, **defaults)
        
    def propagateRay(self, ray):
        """
        Diffract ray. 
        This function may create and return new rays.
        """
        surface = self.surfaces[0]
        p1, ai = surface.intersectRay(ray)
        try:
            sign_incidence_angle = np.sign(ai)
        except:
            pass
        
        if p1 is not None:
            p1 = surface.mapToItem(ray, p1)
            rd = ray['dir']
            a1 = atan2(rd[1], rd[0])
            ray.setEnd(p1)
            wl = ray['wl']/1000 # wavelength
            # print(rd)
            # print(ai)
            # print(a1)
            
            try:
                if sign_incidence_angle < 0:
                    ai = np.abs(ai)
                    ar = a1 + np.pi + ai - asin(wl/self.pitch - sin(ai))
                else:
                    ar = a1 + np.pi - ai + asin(wl/self.pitch - sin(ai))
            except ValueError:
                ar = np.nan
                
            dp = Point(cos(ar), sin(ar))
            ray = Ray(parent=ray, dir=dp)
        else:
            ray.setEnd(None)
        return [ray]

# class Grating2(Optic):
#     def __init__(self, **params):
#         defaults = {
#             'r1': 0,
#             'r2': 0,
#             'd': 0.01,
#             'Groove':300,
#             'name':'Grating'
#         }
#         defaults.update(params)
#         d = defaults.pop('d')
#         defaults['x1'] = -d/2.
#         defaults['x2'] = d/2.
#         self.pitch = 1000/defaults.pop('Groove')
#         self.name = defaults.pop('name')
#         gitem = CircularSolid(brush=(100,100,100,255), **defaults)
#         Optic.__init__(self, self.name, gitem, **defaults)

#     def propagateRay(self, ray):
#         surface = self.surfaces[0]
#         p1, ai = surface.intersectRay(ray)
#         rays = []  # To store the resulting rays
#         try:
#             sign_incidence_angle = np.sign(ai)
#         except:
#             pass

#         if p1 is not None:
#             p1 = surface.mapToItem(ray, p1)
#             rd = ray['dir']
#             ray.setEnd(p1)  # Update the endpoint of the original ray

#             # Calculate the reflected ray
#             p1 = surface.mapToItem(ray, p1)
#             rd = ray['dir']
#             ray.setEnd(p1)
#             a1 = atan2(rd[1], rd[0])
#             ar = a1 + np.pi - 2 * ai
#             dp = Point(cos(ar), sin(ar))
#             ray = Ray(parent=ray, dir=dp)
            
#             reflected_ray = Ray(start=p1, dir=dp, wl=ray['wl'], ior=ray['ior'])
#             rays.append(reflected_ray)

#             # Calculate the diffracted ray
#             p1 = surface.mapToItem(ray, p1)
#             rd = ray['dir']
#             a1 = atan2(rd[1], rd[0])
#             ray.setEnd(p1)
#             wl = ray['wl']/1000 # wavelength
#             try:
#                 if sign_incidence_angle < 0:
#                     ai = np.abs(ai)
#                     ar = a1 + np.pi + ai - asin(wl/self.pitch - sin(ai))
#                 else:
#                     ar = a1 + np.pi - ai + asin(wl/self.pitch - sin(ai))
#             except ValueError:
#                 ar = np.nan
                
#             dp = Point(cos(ar), sin(ar))
#             ray = Ray(parent=ray, dir=dp)
#             diffracted_ray = Ray(parent=ray, dir=dp)
#             rays.append(diffracted_ray)
#         else:
#             ray.setEnd(None)

#         return rays

# class BeamSplitter(Optic):
#     """
#     Represents a beam splitter in the optical simulation. 
#     A beam splitter divides an incoming ray into two parts: a transmitted ray that continues in the same direction, 
#     and a reflected ray that is deflected at a 90-degree angle.
#     """

#     def __init__(self, **params):
#         """
#         Initializes a BeamSplitter object with specified properties.
#         Parameters:
#         - params: A dictionary containing the properties of the beam splitter, such as position and orientation.
#         """
#         super(BeamSplitter, self).__init__(**params)
#         self.name = params.get('name', 'BeamSplitter')

#     def propagateRay(self, ray):
#         """
#         Simulates the interaction of a ray with the beam splitter, generating a transmitted ray and a reflected ray at a 90-degree angle.
#         Parameters:
#         - ray: The incoming Ray object.
#         Returns:
#         - A list containing the transmitted and reflected Ray objects.
#         """
#         # Calculate the transmitted ray (continues in the same direction)
#         transmitted_ray = Ray(start=ray['end'], dir=ray['dir'], wl=ray['wl'], ior=ray['ior'])

#         # Calculate the reflected ray (deflected at a 90-degree angle)
#         angle_of_incidence = np.arctan2(ray['dir'].y(), ray['dir'].x())
#         reflected_angle = angle_of_incidence + np.pi / 2  # 90 degrees in radians
#         reflected_dir = Point(np.cos(reflected_angle), np.sin(reflected_angle))
#         reflected_ray = Ray(start=ray['end'], dir=reflected_dir, wl=ray['wl'], ior=ray['ior'])
#         return [transmitted_ray, reflected_ray]

class CircularSolid(pg.GraphicsObject, ParamObj):
    """
    Represents a solid object with circular or flat surfaces in the simulation. 
    This class is used to visually represent optical elements such as lenses or mirrors with a specific shape.
    Inherits from pg.GraphicsObject for graphical representation and ParamObj for dynamic parameter management.
    """
    def __init__(self, pen=None, brush=None, **opts):
        """
        Initializes a CircularSolid object with visual properties and dimensions.
        Parameters:
        - pen: The pen used to outline the solid. If None, a default pen is used.
        - brush: The brush used to fill the solid. If None, a default brush is used.
        - opts: Additional parameters defining the solid's properties, such as radius and diameter.

        Arguments for each surface are:
        x1,x2 - position of center of _physical surface_
        r1,r2 - radius of curvature
        d1,d2 - diameter of optic
        """
        defaults = dict(x1=-2, r1=100, d1=25.4, x2=2, r2=100, d2=25.4)
        defaults.update(opts)
        ParamObj.__init__(self)
        self.surfaces = [CircleSurface(defaults['r1'], defaults['d1']), CircleSurface(-defaults['r2'], defaults['d2'])]
        pg.GraphicsObject.__init__(self)
        for s in self.surfaces:
            s.setParentItem(self)
        
        if pen is None:
            self.pen = pg.mkPen((220,220,255,200), width=1, cosmetic=True)
        else:
            self.pen = pg.mkPen(pen)
        
        if brush is None: 
            self.brush = pg.mkBrush((230, 230, 255, 30))
        else:
            self.brush = pg.mkBrush(brush)

        self.setParams(**defaults)

    def paramStateChanged(self):
        self.updateSurfaces()

    def updateSurfaces(self):
        self.surfaces[0].setParams(self['r1'], self['d1'])
        self.surfaces[1].setParams(-self['r2'], self['d2'])
        self.surfaces[0].setPos(self['x1'], 0)
        self.surfaces[1].setPos(self['x2'], 0)
        
        self.path = QtGui.QPainterPath()
        self.path.connectPath(self.surfaces[0].path.translated(self.surfaces[0].pos()))
        self.path.connectPath(self.surfaces[1].path.translated(self.surfaces[1].pos()).toReversed())
        self.path.closeSubpath()
        
    def boundingRect(self):
        return self.path.boundingRect()
        
    def shape(self):
        """
        Returns the QPainterPath defining the shape of the solid. 
        Used for collision detection and other interactions within the scene.
        """
        return self.path
    
    def paint(self, p, *args):
        """
        Paints the solid on the scene using the QPainter provided. 
        This method is called by the scene to render the solid.

        Parameters:
        - p: The QPainter to use for painting the solid.
        - args: Additional arguments (not used in this implementation).
        """
        p.setRenderHints(p.renderHints() | p.RenderHint.Antialiasing)
        p.setPen(self.pen)
        p.fillPath(self.path, self.brush)
        p.drawPath(self.path)

class CircleSurface(pg.GraphicsObject):
    """
    Represents a single surface of an optical element. 
    This can be either a flat surface or a curved surface of a specific radius, 
    simulating the behavior of optical elements like lenses and mirrors.
    Inherits from pg.GraphicsObject for graphical representation.
    """
    def __init__(self, radius=None, diameter=None):
        """
        Initializes a CircleSurface object with a specified radius and diameter.

        Parameters:
        - radius: The radius of curvature of the surface. 
        A value of 0 indicates a flat surface.
        Positive values indicate convex surfaces, and negative values indicate concave surfaces.
        - diameter: The diameter of the surface, defining its size.
        """
        pg.GraphicsObject.__init__(self)
        
        self.r = radius
        self.d = diameter
        self.mkPath()
        
    def setParams(self, r, d):
        """
        Updates the parameters of the surface and regenerates its graphical representation.
        Parameters:
        - r: The new radius of curvature.
        - d: The new diameter of the surface.
        """
        self.r = r
        self.d = d
        self.mkPath()
        
    def mkPath(self):
        """
        Generates the QPainterPath representing the surface based on its radius and diameter.
        """
        self.prepareGeometryChange()
        r = self.r
        d = self.d
        h2 = d/2.
        self.path = QtGui.QPainterPath()
        if r == 0:  ## flat surface
            self.path.moveTo(0, h2)
            self.path.lineTo(0, -h2)
        else:
            ## half-height of surface can't be larger than radius
            h2 = min(h2, abs(r))
            arc = QtCore.QRectF(0, -r, r*2, r*2)
            a1 = degrees(asin(h2/r))
            a2 = -2*a1
            a1 += 180.
            self.path.arcMoveTo(arc, a1)
            self.path.arcTo(arc, a1, a2)
        self.h2 = h2
        
    def boundingRect(self):
        return self.path.boundingRect()
        
    def paint(self, p, *args):
        return  ## usually we let the optic draw.
            
    def intersectRay(self, ray):
        """
        Calculates the point of intersection and the angle of incidence between the surface and a ray.

        This method is essential for simulating optical phenomena such as reflection and refraction.
        It determines where a ray of light would intersect the surface of the optical element and at
        what angle, based on the geometry of the surface (flat or curved) and the direction of the ray.

        Parameters:
        - ray: The ray object that contains information about its current position and direction.

        Returns:
        - A tuple containing the point of intersection (as a Point object) and the angle of incidence
        (in radians). Returns (None, None) if there is no intersection.

        The method handles both flat and curved surfaces by calculating the intersection point differently
        based on the radius of curvature (r). 
        For flat surfaces (r=0), a simple geometric calculation is used.
        For curved surfaces, the intersection point is found by solving the equations that represent the
        ray path and the surface curvature.
        """
        ## return the point of intersection and the angle of incidence
        # print "intersect ray"
        h = self.h2
        r = self.r
        p, dir = ray.currentState(relativeTo=self)  # position and angle of ray in local coords.
        #print "  ray: ", p, dir
        p = p - Point(r, 0)  ## move position so center of circle is at 0,0
        #print "  adj: ", p, r
        
        if r == 0:
            #print "  flat"
            if dir[0] == 0:
                y = 0
            else:
                y = p[1] - p[0] * dir[1]/dir[0]
            if abs(y) > h:
                return None, None
            else:
                return (Point(0, y), atan2(dir[1], dir[0]))
        else:
            #print "  curve"
            ## find intersection of circle and line (quadratic formula)
            dx = dir[0]
            dy = dir[1]
            dr = hypot(dx, dy)  # length
            D = p[0] * (p[1]+dy) - (p[0]+dx) * p[1]
            idr2 = 1.0 / dr**2
            disc = r**2 * dr**2 - D**2
            if disc < 0:
                return None, None
            disc2 = disc**0.5
            if dy < 0:
                sgn = -1
            else:
                sgn = 1

            br = self.path.boundingRect()
            x1 = (D*dy + sgn*dx*disc2) * idr2
            y1 = (-D*dx + abs(dy)*disc2) * idr2
            if br.contains(x1+r, y1):
                pt = Point(x1, y1)
            else:
                x2 = (D*dy - sgn*dx*disc2) * idr2
                y2 = (-D*dx - abs(dy)*disc2) * idr2
                pt = Point(x2, y2)
                if not br.contains(x2+r, y2):
                    return None, None
                
            norm = atan2(pt[1], pt[0])
            if r < 0:
                norm += np.pi
            dp = p - pt
            ang = atan2(dp[1], dp[0]) 
            return pt + Point(r, 0), ang-norm

class Ray(pg.GraphicsObject, ParamObj):
    """
    Represents a single segment of a light ray in the optical simulation. 
    This class is responsible for managing the properties of the ray such as its direction, wavelength, and the index of
    refraction (ior) at its current segment.

    Attributes:
    - ior: The index of refraction of the medium through which the ray is currently traveling.
    - wl: The wavelength of the ray, which can affect how it interacts with optical elements due to dispersion.
    - end: The end point of the ray segment. If None, the ray is considered to extend infinitely in its direction.
    - dir: The direction vector of the ray, indicating the direction in which the ray is propagating.
    """
    sigStateChanged = QtCore.Signal()
    
    def __init__(self, **params):
        """
        Initializes a Ray object with specified properties.

        Parameters:
        - params: 
        A dictionary containing the initial properties of the ray, such as 'start', 'end', 
        'dir' (direction), 'wl' (wavelength), 'ior' (index of refraction), and 'Laser' (the name of the laser source).
        """
        ParamObj.__init__(self)
        defaults = {
            'ior': 1.0,
            'wl': 500,
            'end': None,
            'dir': Point(1,0),
        }
        self.params = {}
        pg.GraphicsObject.__init__(self)
        self.children = []
        parent = params.get('parent', None)
        if parent is not None:
            defaults['start'] = parent['end']
            defaults['wl'] = parent['wl']
            defaults['Laser'] = parent['Laser']
            self['ior'] = parent['ior']
            self['dir'] = parent['dir']
            self['WL_min'] = parent['WL_min']
            self['WL_max'] = parent['WL_max']
            parent.addChild(self)
        
        defaults.update(params)
        defaults['dir'] = Point(defaults['dir'])
        self.setParams(**defaults)
        self.mkPath()
        
    def clearChildren(self):
        """
        Clears any child rays that have been generated by this ray, such as rays resulting from refraction or reflection. 
        This is useful for resetting the simulation or preparing for a new calculation.
        """
        for c in self.children:
            c.clearChildren()
            c.setParentItem(None)
            self.scene().removeItem(c)
        self.children = []
        
    def paramStateChanged(self):
        """
        Called when any parameter of the ray changes. 
        This method can be overridden by subclasses to perform custom actions in response to parameter changes, such as updating the simulation.
        """
        pass
        
    def addChild(self, ch):
        """
        Adds a child ray to this ray. Child rays can represent secondary rays generated through
        interactions with optical elements, such as refraction or reflection.

        Parameters:
        - ch: The child Ray object to be added.
        """
        self.children.append(ch)
        ch.setParentItem(self)
        
    def currentState(self, relativeTo=None):
        """
        Returns the current state of the ray, including its position and direction, optionally relative to another object in the scene.
        Parameters:
        - relativeTo: An optional graphics object to which the ray's state should be relative.
        Returns: A tuple containing the ray's current position and direction.
        """
        pos = self['start']
        dir = self['dir']
        if relativeTo is None:
            return pos, dir
        else:
            trans = self.itemTransform(relativeTo)[0]
            p1 = trans.map(pos)
            p2 = trans.map(pos + dir)
            return Point(p1), Point(p2-p1)
            
    def setEnd(self, end):
        """
        Sets the end point of the ray segment. Useful for updating the ray's path after interactions with optical elements.
        Parameters:
        - end: The new end point of the ray segment.
        """
        self['end'] = end
        self.mkPath()

    def boundingRect(self):
        return self.path.boundingRect()
        
    def paint(self, p, *args):
        # p.setPen(pg.mkPen((255,0,0, 150)))
        p.setRenderHints(p.renderHints() | p.RenderHint.Antialiasing)
        p.setCompositionMode(p.CompositionMode.CompositionMode_Plus)
        p.setPen(wlPen(self['wl'],self['WL_min'],self['WL_max']))
        p.drawPath(self.path)
        
    def mkPath(self):
        """
        Generates the QPainterPath representing the ray segment. 
        This method is called internally to update the ray's graphical representation based on its current properties.
        """
        self.prepareGeometryChange()
        self.path = QtGui.QPainterPath()
        self.path.moveTo(self['start'])
        if self['end'] is not None:
            self.path.lineTo(self['end'])
        else:
            self.path.lineTo(self['start']+500*self['dir'])

def trace(rays, optics):
    """
    Recursively propagates a list of rays through a sequence of optical elements, simulating
    the behavior of each ray as it encounters each optic in turn.

    This function forms the core of the ray tracing algorithm, allowing for the simulation
    of complex optical systems. 
    Each ray is updated based on its interaction with optical elements, which can include reflection, 
    refraction, and absorption, depending on the nature of the element and the properties of the ray.

    Parameters:
    - rays: 
    A list of Ray objects representing the light rays to be propagated through the optical system.
    - optics: 
    A list of optical elements (instances of Optic or its subclasses) that the rays will encounter. 
    The order of the elements in the list represents the sequence in which the rays will interact with them.

    The function iterates over each ray in the list, propagating it through each optical element
    in the 'optics' list. 
    For each element, the ray's path is updated based on the specific optical interactions defined 
    by the element's 'propagateRay' method. 
    After a ray interacts with an element, it may split into multiple rays, be absorbed, or continue unchanged,
    depending on the physical properties of the element and the ray itself.

    The recursive nature of the function allows for the simulation of multiple reflections and
    refractions as rays pass through or reflect off multiple elements in the system.
    """
    if len(optics) < 1 or len(rays) < 1:
        return
    for r in rays:
        r.clearChildren()
        o = optics[0]
        r2 = o.propagateRay(r)
        trace(r2, optics[1:])

class Tracer(QtCore.QObject):
    """
    A simple ray tracer designed to propagate rays through a sequence of optical elements and
    simulate the interactions between those rays and the elements. 
    This class oversees the entire process of ray tracing within an optical system, updating the paths of rays as they
    encounter various optical components.

    The Tracer uses a list of rays and a list of optics to perform the simulation, applying
    the optical properties and behaviors of each element to the rays as they pass through.
    This approach allows for the dynamic simulation of complex optical systems, including
    lenses, mirrors, gratings, and more.
    """
    def __init__(self, rays, optics):
        """
        Initializes the Tracer with a list of rays and optical elements.

        Parameters:
        - rays: A list of Ray objects that will be traced through the optical system.
        - optics: 
        A list of optical elements (e.g., instances of Optic or its subclasses) that the rays will interact with. 
        The order in the list determines the sequence of interaction.
        """
        QtCore.QObject.__init__(self)
        self.optics = optics
        self.rays = rays
        for o in self.optics:
            o.sigStateChanged.connect(self.trace)
        self.trace()
            
    def trace(self):
        """
        Propagates each ray through the list of optical elements, updating their paths based
        on the interactions with each element. 
        This method forms the core of the ray tracing process, applying the effects of each optical element to the rays.

        As rays are propagated, they may be reflected, refracted, or absorbed depending on
        the properties of the optical elements they encounter. 
        This method updates the ray paths accordingly, simulating the physical behavior of light within the system.
        """
        trace(self.rays, self.optics)
