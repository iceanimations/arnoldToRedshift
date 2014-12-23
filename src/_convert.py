import os.path as osp
from uiContainer import uic
import qtify_maya_window as qtfy
import pymel.core as pc
import msgBox
from PyQt4.QtGui import QMessageBox, qApp

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
            return pc.shadingNode(pc.nt.RedshiftArchitectural, asShader=True)
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
    
    def lambertToRedshift(self):
        lamberts = pc.ls(sl=True, type=pc.nt.Lambert)
        self.toRedshift(lamberts)
    
    def arnoldToRedshift(self):
        arnolds = self.getArnolds()
        self.toRedshift(arnolds)
    
    def toRedshift(self, nodes):
        self.progressBar.setMaximum(len(nodes))
        count = 1
        for node in nodes:
            redshift = self.creatRedshift()
            if redshift is not None:
                try:
                    node.color.inputs(plugs=True)[0].connect(redshift.diffuse)
                except IndexError:
                    redshift.diffuse.set(node.color.get())
                try:
                    node.normalCamera.inputs(plugs=True)[0].connect(redshift.bump_input)
                except IndexError:
                    pass
                for sg in pc.listConnections(node, type=pc.nt.ShadingEngine):
                    redshift.outColor.connect(sg.surfaceShader, force=True)
                name = node.name().split(':')[-1].split('|')[-1].replace('aiStandard', 'redshiftArchitectural').replace('lambert', 'redshiftArchitectural')
                pc.delete(node)
                pc.rename(redshift, name)
            else:
                break
            self.progressBar.setValue(count)
            count += 1