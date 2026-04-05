import os
import sys
import importlib.util
from qgis.PyQt.QtGui import QIcon
from qgis.core import (
    QgsProcessingProvider,
    QgsApplication,
    QgsProcessingLayerPostProcessorInterface
)

def load_script(module_name, file_name, plugin_dir):
    """Rakamla başlayan Python dosyalarını güvenli bir şekilde içe aktarır."""
    file_path = os.path.join(plugin_dir, file_name)
    if not os.path.exists(file_path):
        return None
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Hata: {file_name} yuklenemedi. Detay: {e}")
        return None

class StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Katman QGIS harita ekranına yüklendikten sonra QML stilini uygulayan sınıf."""
    def __init__(self, qml_path):
        super().__init__()
        self.qml_path = qml_path

    def postProcessLayer(self, layer, context, feedback):
        if os.path.exists(self.qml_path):
            feedback.pushInfo(f"Stil basariyla uygulaniyor: {os.path.basename(self.qml_path)}")
            layer.loadNamedStyle(self.qml_path)
            layer.triggerRepaint()
        else:
            feedback.pushInfo(f"UYARI: Stil dosyasi bulunamadi -> {self.qml_path}")

class PlanXUIPProvider(QgsProcessingProvider):
    def __init__(self):
        super().__init__()

    def loadAlgorithms(self):
        plugin_dir = os.path.dirname(__file__)
        
        alg1 = load_script("alg1", "1_uip_yol_platform_uretme.py", plugin_dir)
        alg2 = load_script("alg2", "2_uip_yol_kavsak_trim.py", plugin_dir)
        alg3 = load_script("alg3", "3_uip_yol_poligonlasma_alanlari_baglama.py", plugin_dir)
        alg4 = load_script("alg4", "4_uip_yol_cepheleri_segmentleme.py", plugin_dir)
        alg5 = load_script("alg5", "5_uip_ada_nufus_yogunluk_hesaplama.py", plugin_dir)
        alg6 = load_script("alg6", "6_uip_plan_kent_karakter_tablosu.py", plugin_dir)
        alg7 = load_script("alg7", "7_uip_ek2_karakter_tablosu.py", plugin_dir)
        alg8 = load_script("alg8", "8_uip_duzenleme_ortaklik_payi.py", plugin_dir)

        if alg1 and hasattr(alg1, 'GenerateYolPlatformUIP'):
            class Alg1(alg1.GenerateYolPlatformUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_1.svg'))
            self.addAlgorithm(Alg1())
        
        if alg2 and hasattr(alg2, 'JunctionTrimUIP'):
            class Alg2(alg2.JunctionTrimUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_2.svg'))
                def processAlgorithm(self, parameters, context, feedback):
                    results = super().processAlgorithm(parameters, context, feedback)
                    dest_id = results.get('OUTPUT')
                    if dest_id and context.willLoadLayerOnCompletion(dest_id):
                        qml_path = os.path.join(plugin_dir, 'uip_kaavsak_sonrasi_yol_stil.qml')
                        processor = StylePostProcessor(qml_path)
                        # Garbage Collection'i onlemek icin referansi context'e ekliyoruz
                        if not hasattr(context, 'planx_processors'):
                            context.planx_processors = []
                        context.planx_processors.append(processor)
                        context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(processor)
                    return results
            self.addAlgorithm(Alg2())

        if alg3 and hasattr(alg3, 'RoadPolygonizeAndJoinUIP'):
            class Alg3(alg3.RoadPolygonizeAndJoinUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_3.svg'))
            self.addAlgorithm(Alg3())

        if alg4 and hasattr(alg4, 'YolKatsayisiSegmentlemeUIP'):
            class Alg4(alg4.YolKatsayisiSegmentlemeUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_4.svg'))
                def processAlgorithm(self, parameters, context, feedback):
                    results = super().processAlgorithm(parameters, context, feedback)
                    dest_id = results.get('OUTPUT')
                    if dest_id and context.willLoadLayerOnCompletion(dest_id):
                        qml_path = os.path.join(plugin_dir, 'uip_cephe_stil.qml')
                        processor = StylePostProcessor(qml_path)
                        # Garbage Collection'i onlemek icin referansi context'e ekliyoruz
                        if not hasattr(context, 'planx_processors'):
                            context.planx_processors = []
                        context.planx_processors.append(processor)
                        context.layerToLoadOnCompletionDetails(dest_id).setPostProcessor(processor)
                    return results
            self.addAlgorithm(Alg4())

        if alg5 and hasattr(alg5, 'YapiYogunluguVeNufusHesaplaUIP'):
            class Alg5(alg5.YapiYogunluguVeNufusHesaplaUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_5.svg'))
            self.addAlgorithm(Alg5())

        if alg6 and hasattr(alg6, 'PlanKentKarakterTablosuUIP'):
            class Alg6(alg6.PlanKentKarakterTablosuUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_6.svg'))
            self.addAlgorithm(Alg6())

        if alg7 and hasattr(alg7, 'Ek2KarakterTablosuUIP'):
            class Alg7(alg7.Ek2KarakterTablosuUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_7.svg'))
            self.addAlgorithm(Alg7())

        if alg8 and hasattr(alg8, 'DuzenlemeOrtaklikPayiUIP'):
            class Alg8(alg8.DuzenlemeOrtaklikPayiUIP):
                def icon(self): return QIcon(os.path.join(plugin_dir, 'icon_8.svg'))
            self.addAlgorithm(Alg8())

    def id(self):
        return 'planx_uip'

    def name(self):
        return 'planX - UİP Araç Seti'

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon_main.svg'))
