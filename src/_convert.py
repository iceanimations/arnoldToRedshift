import os.path as osp
from uiContainer import uic
import qtify_maya_window as qtfy


root_path = osp.dirname(osp.dirname(__file__))
ui_path = osp.join(root_path, 'ui')

Form, Base = uic.loadUiType(osp.join(ui_path, 'main.ui'))
class Converter(Form, Base):
    def __init__(self, parent=qtfy.getMayaWindow(), standalone=False):
        super(Converter, self).__init__(parent)
        self.setupUi(self)