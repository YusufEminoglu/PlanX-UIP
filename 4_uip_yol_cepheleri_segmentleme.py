# File: 4_uip_yol_cepheleri_segmentleme.py
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsProcessingUtils
)
from qgis.PyQt.QtCore import QVariant
import processing

class YolKatsayisiSegmentlemeUIP(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                'UİP Trimlenmiş Yol Katmanı (Çizgi)',
                [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                '10m Segmentli Yol Cepheleri (UİP)'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        feedback.pushInfo("1. Sadece dış sınırlar (left_outer, right_outer) filtreleniyor...")
        
        # Native QGIS algoritması ile veri filtreleme işlemi (Child Algorithm)
        extract_result = processing.run(
            "native:extractbyexpression",
            {
                'INPUT': parameters[self.INPUT],
                'EXPRESSION': "\"side\" IN ('left_outer', 'right_outer')",
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            context=context, feedback=feedback, is_child_algorithm=True
        )
        
        extracted_layer_id = extract_result['OUTPUT']

        feedback.pushInfo("2. Dış sınırlar analitik çözünürlük için 10 metrelik segmentlere bölünüyor...")
        
        split_result = processing.run(
            "native:splitlinesbylength",
            {
                'INPUT': extracted_layer_id,
                'LENGTH': 10,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            },
            context=context, feedback=feedback, is_child_algorithm=True
        )
        
        split_layer_id = split_result['OUTPUT']
        
        # Hafızadaki geçici katmanın veri nesnesine dönüştürülmesi
        split_layer_obj = QgsProcessingUtils.mapLayerFromString(split_layer_id, context)
        
        if not split_layer_obj or split_layer_obj.featureCount() == 0:
            feedback.reportError("Filtreleme veya segmentleme sonucunda detay bulunamadı. Verinin 'side' özniteliğini kontrol ediniz.")
            return {self.OUTPUT: None}

        yeni_alanlar = QgsFields(split_layer_obj.fields())
        yeni_alanlar.append(QgsField('katsayi', QVariant.Double))
        yeni_alanlar.append(QgsField('cephe_tipi', QVariant.String))

        (sink, sink_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, yeni_alanlar,
            split_layer_obj.wkbType(), split_layer_obj.sourceCrs()
        )

        feedback.pushInfo("3. Mekansal katsayılar ve cephe tipleri hesaplanarak katmana yazılıyor...")
        
        total_features = split_layer_obj.featureCount()
        
        # Yol katsayısı matrisi
        katsayi_map = {
            'ERİŞME KONTROLLÜ KARAYOLU (OTOYOL)': 2.5,
            'BÖLÜNMÜŞ TAŞIT YOLU': 1.6,
            'TAŞIT YOLU': 1.0,
            'YAYA YOLU VE BÖLGESİ': 0.4
        }
        
        valid_cephe_tipleri = [
            'DÜZELTİLEN CEPHE ÇİZGİSİ', 
            'KORUNAN CEPHE ÇİZGİSİ', 
            'ÖNERİLEN CEPHE ÇİZGİSİ'
        ]

        for i, feat in enumerate(split_layer_obj.getFeatures()):
            if feedback.isCanceled():
                break
                
            attr = list(feat.attributes())
            
            # String parsing ve veri tutarsızlıklarını önleme
            yol_tipi = str(feat['yolTipi']).strip().upper() if feat['yolTipi'] else ""
            cephe_degeri = str(feat['type']).strip().upper() if feat['type'] else ""

            katsayi = katsayi_map.get(yol_tipi, None)
            cephe_tipi = feat['type'] if cephe_degeri in valid_cephe_tipleri else None

            yeni_feat = QgsFeature()
            yeni_feat.setGeometry(feat.geometry())
            yeni_feat.setFields(yeni_alanlar)
            yeni_feat.setAttributes(attr + [katsayi, cephe_tipi])
            sink.addFeature(yeni_feat, QgsFeatureSink.FastInsert)
            
            if total_features > 0:
                feedback.setProgress(int((i / total_features) * 100))

        return {self.OUTPUT: sink_id}

    def name(self):
        return '4_uip_yol_cepheleri_segmentleme'

    def displayName(self):
        return '4. Yol Cepheleri Katsayısı ve Segmentleme (1/1000 UİP)'

    def group(self):
        return 'UİP Yol İşlemleri'

    def groupId(self):
        return 'uip_yol_islemleri'

    def createInstance(self):
        return YolKatsayisiSegmentlemeUIP()