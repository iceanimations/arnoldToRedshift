import os.path as osp
from uiContainer import uic
import qtify_maya_window as qtfy
import pymel.core as pc
import msgBox
from PyQt4.QtGui import QMessageBox, qApp
import appUsageApp

root_path = osp.dirname(osp.dirname(__file__))
ui_path = osp.join(root_path, 'ui')

Form, Base = uic.loadUiType(osp.join(ui_path, 'main.ui'))
class Converter(Form, Base):
    def __init__(self, parent=qtfy.getMayaWindow(), standalone=False):
        super(Converter, self).__init__(parent)
        self.setupUi(self)
        
        self.title = 'Redshift Converter'
        
        self.progressBar.hide()
        
        self.convertButton.clicked.connect(self.callConvert)
        self.selectButton.clicked.connect(self.selectShaders)
        map(lambda btn: btn.clicked.connect(self.setToolTipForSelectButton), [self.lambertToRedshiftButton,
                                                                              self.arnoldToLambertButton,
                                                                              self.arnoldToRedshiftButton])
        
        appUsageApp.updateDatabase('ToRedshift')
    
    def setToolTipForSelectButton(self):
        if self.lambertToRedshiftButton.isChecked():
            self.selectButton.setToolTip('Select all lamberts')
        else:
            self.selectButton.setToolTip('Select all arnolds')
    
    def setStatus(self, status):
        self.statusBar.showMessage(status, 2000)
        
    def selectShaders(self):
        length = 0
        if self.lambertToRedshiftButton.isChecked():
            shaders = pc.ls(type=pc.nt.Lambert)
            length = len(shaders)
            pc.select(shaders)
        else:
            try:
                shaders = pc.ls(type=pc.nt.AiStandard)
                length = len(shaders)
                pc.select(shaders)
            except AttributeError:
                msgBox.showMessage(self, title=self.title,
                                   msg='It seems like Arnold is either not loaded or not installed',
                                   icon=QMessageBox.Information)
        self.setStatus(str(length) +' shaders selected')

    def closeEvent(self, event):
        self.deleteLater()
        del self
        
    def callConvert(self):
        self.progressBar.show()
        if self.arnoldToLambertButton.isChecked():
            self.arnoldToLambert()
        elif self.arnoldToRedshiftButton.isChecked():
            self.arnoldToRedshift()
        else:
            self.lambertToRedshift()
        self.progressBar.setValue(0)
        self.progressBar.hide()
            
    def creatRedshift(self):
        try:
            node = pc.shadingNode(pc.nt.RedshiftArchitectural, asShader=True)
            node.reflectivity.set(0)
            return node
        except AttributeError:
            msgBox.showMessage(self, title=self.title,
                               msg='It seems like Redshift is either not loaded or not installed',
                               icon=QMessageBox.Information)

    def createRedshiftBump(self):
        try:
            node = pc.shadingNode(pc.nt.RedshiftBumpMap, asUtility=True)
            return node
        except AttributeError:
            msgBox.showMessage(self, title=self.title,
                               msg='It seems like Redshift is either not loaded or not installed',
                               icon=QMessageBox.Information)

    
    def getArnolds(self):
        try:
            return pc.ls(sl=True, type=pc.nt.AiStandard)
        except AttributeError, ex:
            msgBox.showMessage(self, title=self.title,
                               msg='It seems like Arnold is either not loaded or not installed',
                               icon=QMessageBox.Information)
            return []

    def arnoldToLambert(self):
        arnolds = self.getArnolds()
        if not arnolds:
            self.noSelectionMsg()
            return
        self.progressBar.setMaximum(len(arnolds))
        count = 1
        for node in arnolds:
            lambert = pc.shadingNode(pc.nt.Lambert, asShader=True)
            try:
                node.color.inputs(plugs=True)[0].connect(lambert.color)
            except IndexError:
                lambert.color.set(node.color.get())
            try:
                node.normalCamera.inputs(plugs=True)[0].connect(lambert.normalCamera)
            except IndexError:
                pass
            for sg in pc.listConnections(node, type=pc.nt.ShadingEngine):
                lambert.outColor.connect(sg.surfaceShader, force=True)
            name = node.name().split(':')[-1].split('|')[-1].replace('aiStandard', 'lambert')
            pc.delete(node)
            pc.rename(lambert, name)
            self.progressBar.setValue(count)
            qApp.processEvents()
            count += 1
            
    def noSelectionMsg(self):
        msgBox.showMessage(self, title=self.title,
                           msg='No source shader selected',
                           icon=QMessageBox.Information)
    
    def lambertToRedshift(self):
        lamberts = pc.ls(sl=True, type=pc.nt.Lambert)
        if not lamberts:
            self.noSelectionMsg()
            return
        self.toRedshift(lamberts)
    
    def arnoldToRedshift(self):
        arnolds = self.getArnolds()
        if not arnolds:
            self.noSelectionMsg()
            return
        self.toRedshift(arnolds)
    
    def replaceAttr(self, fromattr, toattr, invert=False):
        try:
            fromattr = self.arnold.attr(fromattr)
            toattr = self.redshift.attr(toattr)
            fromattr.inputs(plugs=True)[0].connect(toattr)
        except IndexError:
            if invert:
                toattr.set(1-fromattr.get())
            else:
                toattr.set(fromattr.get())
        except Exception:
            pass

    def toRedshift(self, nodes):
        self.progressBar.setMaximum(len(nodes))
        count = 1
        for node in nodes:

            redshift = self.creatRedshift()
            self.arnold = node
            self.redshift = redshift
            if redshift is not None:

                #Diffuse colors
                self.replaceAttr('color', 'diffuse')

                #Speculars
                self.replaceAttr('specularRoughness', 'refl_gloss', invert=True)
                self.replaceAttr('KsColor', 'refl_color')
                self.replaceAttr('Ks', 'reflectivity')

                #Anisotropy
                self.replaceAttr('specularAnisotropy', 'anisotropy')
                self.replaceAttr('specularRotation', 'anisotropy_rotation')

                # Subsurface
                try:
                    if node.Ksss.get() or node.Ksss.inputs():
                        redshift.refr_translucency.set(True)
                        self.replaceAttr('Ksss', 'refr_trans_weight')
                        self.replaceAttr('KsssColor', 'refr_trans_color')
                except: pass

                # Bump Mapping
                try:
                    bump = node.normalCamera.inputs()[0]
                    rsbump = self.createRedshiftBump()
                    inputnode = bump.bumpValue.inputs()[0]
                    inputnode.outColor.connect(rsbump.input)
                    try:
                        rsbump.outDisplacementVector.connect(redshift.bump_input)
                    except:
                        rsbump.out.connect(redshift.bump_input)
                    rsbump.scale.set(pc.dt.clamp(bump.bumpDepth.get()/10.0,
                        0.001, 100.0))
                    try:
                        pc.delete(bump)
                    except:
                        pass

                except IndexError:
                    try:
                        node.normalCamera.inputs(plugs=True)[0].connect(redshift.bump_input)
                    except IndexError:
                        pass


                for sg in pc.listConnections(node, type=pc.nt.ShadingEngine):
                    redshift.outColor.connect(sg.surfaceShader, force=True)
                name = node.name().split(':')[-1].split('|')[-1].replace('aiStandard', 'redshiftArchitectural').replace('lambert', 'redshiftArchitectural')
                try:
                    pc.delete(node)
                except:
                    pass
                try:
                    pc.rename(redshift, name)
                except:
                    pass
            else:
                break
            self.progressBar.setValue(count)
            count += 1
