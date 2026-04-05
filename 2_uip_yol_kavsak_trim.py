# File: 2_uip_yol_kavsak_trim.py
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsWkbTypes,
    QgsFeatureSink,
    QgsSpatialIndex,
    QgsLineString,
    QgsPointXY
)

class JunctionTrimUIP(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    RADIUS = 'RADIUS'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT, 'UİP Yol Platform Katmanı', [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterNumber(self.RADIUS, 'Kavşak Alanı Çapı (metre)', type=QgsProcessingParameterNumber.Double, defaultValue=8.0))
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, 'Kavşakları Trimlenmiş Hatlar'))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        radius = self.parameterAsDouble(parameters, self.RADIUS, context)

        fields = QgsFields(source.fields())
        fields.append(QgsField("parent_fid", QVariant.LongLong))
        fields.append(QgsField("type_link", QVariant.String))
        fields.append(QgsField("parca_no", QVariant.Int))
        fields.append(QgsField("junction_id", QVariant.Int))

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, fields, QgsWkbTypes.MultiLineString, source.sourceCrs())

        centers = []
        others = []
        
        for f in source.getFeatures():
            if f['type'] == 'center': centers.append(f)
            else: others.append(f)

        center_index = QgsSpatialIndex()
        for f in centers: center_index.insertFeature(f)

        feedback.pushInfo("Kavşak noktaları (Spatial Index ile) tespit ediliyor...")
        junction_buffers = []
        outer_buffers = []
        processed_pairs = set()

        for f1 in centers:
            bbox = f1.geometry().boundingBox()
            for fid2 in center_index.intersects(bbox):
                if fid2 == f1.id(): continue
                pair = tuple(sorted((f1.id(), fid2)))
                if pair in processed_pairs: continue
                processed_pairs.add(pair)
                
                f2 = next((x for x in centers if x.id() == fid2), None)
                if not f2: continue

                geom1, geom2 = f1.geometry(), f2.geometry()
                if geom1.intersects(geom2):
                    intersect_geom = geom1.intersection(geom2)
                    pt = intersect_geom.centroid().asPoint()
                    pt_geom = QgsGeometry.fromPointXY(pt)
                    
                    inner_buf = pt_geom.buffer((radius + 1) / 2.0, 8)
                    outer_buf = pt_geom.buffer((radius + 5 + 1) / 2.0, 8)
                    
                    jid = len(junction_buffers)
                    junction_buffers.append((jid, inner_buf))
                    outer_buffers.append((jid, outer_buf))

        # Centerları direkt yazdır
        for f in centers:
            f_copy = QgsFeature(fields)
            f_copy.setGeometry(f.geometry())
            vals = list(f.attributes())
            vals.extend([f.id(), 'center', 0, -1])
            f_copy.setAttributes(vals)
            sink.addFeature(f_copy, QgsFeatureSink.FastInsert)

        feedback.pushInfo("Hatlar trimleniyor...")
        total = len(others)
        
        for i, f in enumerate(others):
            if feedback.isCanceled(): break
            
            orig_geom = f.geometry()
            ftype = f['type']
            side = f['side']
            yol_tipi = f['yolTipi']

            # Not: Veride Null değerler varsa TypeError almamak adına str(side) kullanmak daha güvenli olabilir
            if ftype == 'kaldirim' and side and 'inner' in str(side) and yol_tipi == 'YAYA YOLU VE BÖLGESİ':
                continue

            trimmed_geom = QgsGeometry(orig_geom)
            
            # İç buffer ile kes
            for jid, buf in junction_buffers:
                if trimmed_geom.intersects(buf):
                    trimmed_geom = trimmed_geom.difference(buf)

            if trimmed_geom.isEmpty(): continue

            # Dış buffer mantığını koru
            final_parts = []
            for jid, obuf in outer_buffers:
                if trimmed_geom.intersects(obuf):
                    intersection = trimmed_geom.intersection(obuf)
                    if not intersection.isEmpty():
                        final_parts.append(intersection)
                    trimmed_geom = trimmed_geom.difference(obuf)

            if not trimmed_geom.isEmpty():
                final_parts.append(trimmed_geom)

            # Parçaları kaydet
            for part in final_parts:
                geom_collection = part.asGeometryCollection() if part.isMultipart() else [part]
                for p_idx, subpart in enumerate(geom_collection):
                    if subpart.isEmpty(): continue
                    
                    # Hangi kavşağa değiyor bul
                    junc_id = -1
                    for jid, buf in junction_buffers:
                        if subpart.intersects(buf):
                            junc_id = jid
                            break
                            
                    f_trim = QgsFeature(fields)
                    f_trim.setGeometry(subpart)
                    vals = list(f.attributes())
                    vals.extend([f.id(), 'original', p_idx + 1, junc_id])
                    f_trim.setAttributes(vals)
                    sink.addFeature(f_trim, QgsFeatureSink.FastInsert)
                    
            if total > 0: feedback.setProgress(int(i / total * 100))

        return {self.OUTPUT: dest_id}

    def name(self): return '2_uip_kavsak_trim_explode'
    def displayName(self): return '2. Kavşakları Temizle ve Ayır (1/1000 UİP)'
    def group(self): return 'UİP Yol İşlemleri'
    def groupId(self): return 'uip_yol_islemleri'
    def createInstance(self): return JunctionTrimUIP()