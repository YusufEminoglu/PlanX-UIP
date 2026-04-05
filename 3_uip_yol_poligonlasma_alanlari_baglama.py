# File: 3_uip_yol_poligonlasma_alanlari_baglama.py
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsProcessingUtils
)
import processing

class RoadPolygonizeAndJoinUIP(QgsProcessingAlgorithm):
    INPUT_LINES = 'INPUT_LINES'
    INPUT_ZONES = 'INPUT_ZONES'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT_LINES, 'UİP Çizgi Katmanı (Trimlenmiş)', [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT_ZONES, 'Referans Poligon Katmanı (UİP Plan)', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, 'UİP Yol Poligonları'))

    def processAlgorithm(self, parameters, context, feedback):
        feedback.pushInfo("1. Dış sınırlar filtreleniyor...")
        # UİP için left_outer ve right_outer yolların dış zarfını ifade eder
        expression = "\"side\" ILIKE '%outer%'"
            
        extract_result = processing.run("native:extractbyexpression", {
            'INPUT': parameters[self.INPUT_LINES],
            'EXPRESSION': expression,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }, context=context, feedback=feedback, is_child_algorithm=True)
        
        extracted_layer_id = extract_result['OUTPUT']
        extracted_layer_obj = QgsProcessingUtils.mapLayerFromString(extracted_layer_id, context)
        
        if not extracted_layer_obj or extracted_layer_obj.featureCount() == 0:
            feedback.reportError("Filtre sonucunda hiç dış hat bulunamadı!")
            return {self.OUTPUT: None}

        feedback.pushInfo("2. Çizgiler poligona dönüştürülüyor...")
        poly_result = processing.run("native:polygonize", {
            'INPUT': extracted_layer_id,
            'KEEP_FIELDS': False, 
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }, context=context, feedback=feedback, is_child_algorithm=True)

        poly_layer_id = poly_result['OUTPUT']
        poly_layer_obj = QgsProcessingUtils.mapLayerFromString(poly_layer_id, context)

        if not poly_layer_obj or poly_layer_obj.featureCount() == 0:
            feedback.reportError("Topoloji hatası! Çizgiler kapalı bir alan (poligon) oluşturamadı.")
            return {self.OUTPUT: None}

        feedback.pushInfo("3. Mekansal Eşleme (Largest Overlap) yapılıyor...")
        final_result = processing.run("native:joinattributesbylocation", {
            'INPUT': poly_layer_id,
            'JOIN': parameters[self.INPUT_ZONES],
            'PREDICATE': [0], 
            'METHOD': 2, 
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': parameters[self.OUTPUT]
        }, context=context, feedback=feedback, is_child_algorithm=True)

        return {self.OUTPUT: final_result['OUTPUT']}

    def name(self): return '3_uip_yol_poligon_join'
    def displayName(self): return '3. Yol Poligonlaştır ve Eşle (1/1000 UİP)'
    def group(self): return 'UİP Yol İşlemleri'
    def groupId(self): return 'uip_yol_islemleri'
    def createInstance(self): return RoadPolygonizeAndJoinUIP()