<div align="center">

<img src="icon.svg" width="96" alt="PlanX UIP Toolset icon"/>

# PlanX UIP Toolset

**Automated Uygulama İmar Planı (Turkish master plan) toolset for QGIS — rapid base layers and layouts in 8 stages (Processing).**

[![QGIS](https://img.shields.io/badge/QGIS-3.0%2B-93b023?logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/planx_uip_arac_seti/)
[![Version](https://img.shields.io/github/v/tag/YusufEminoglu/PlanX-UIP?label=version&color=blue)](https://github.com/YusufEminoglu/PlanX-UIP/releases)
[![License](https://img.shields.io/badge/license-GPL--3.0-orange)](LICENSE)
[![QGIS Plugin Hub](https://img.shields.io/badge/QGIS%20Hub-install-589632?logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/planx_uip_arac_seti/)

</div>

---

## Why PlanX UIP Toolset?

Producing a 1/1000-scale Uygulama İmar Planı involves a chain of repetitive geometry and table work: road platforms, junction cleanups, facade segmentation, density tables. This toolset automates the whole implementation pipeline as sequential Processing algorithms, built with feedback from educational workflows at Dokuz Eylül University, Department of City and Regional Planning.

## ✨ Features

- **8-stage sequential pipeline** — from road centerlines to the regulatory EK-2 character table.
- **Smart post-processing** — QML styles are assigned automatically after Junction Trim and Facade Segmentation.
- **Regulatory outputs** — urban character tables, EK-2 tables and Düzenleme Ortaklık Payı (DOP) ratios.
- **Processing-native** — every stage is a `QgsProcessingAlgorithm`, scriptable in models and batch runs.
- **Hierarchical, icon-supported layout** in the Processing Toolbox.

## 🚀 Installation

**From the QGIS Plugin Hub (recommended):** `Plugins → Manage and Install Plugins…` → search for **"PlanX UIP"** → *Install*.

**From a release zip:** download the latest zip from [Releases](https://github.com/YusufEminoglu/PlanX-UIP/releases) → `Plugins → Install from ZIP`.

Requires QGIS 3.0 or newer. No external Python dependencies.

## 📖 Quick start

1. Install and activate the plugin — tools appear under **Processing Toolbox → PlanX UIP Toolset**.
2. Load your road centerline and parcel layers.
3. Run the stages in order, starting with **1 — Road Platform Generator**.
4. Each stage's output feeds the next; styled layers are added automatically.

## ⚙️ The 8-stage workflow

| # | Tool | What it does |
|---|------|--------------|
| 1 | **Road Platform Generator** | Produces road platform polygons from centerlines |
| 2 | **Junction Trim** | Cleans intersection areas and trims overlapping road polygons |
| 3 | **Road Polygon Area Connector** | Links road polygonalization areas to the network |
| 4 | **Facade Segmentation** | Segments parcel facades and classifies frontages |
| 5 | **Block Population Density** | Calculates population density per block |
| 6 | **Urban Character Table** | Generates plan character (kentsel karakter) summary tables |
| 7 | **EK-2 Character Table** | Produces the regulatory EK-2 character table |
| 8 | **Düzenleme Ortaklık Payı (DOP)** | Computes land readjustment share ratios |

Full version history: [CHANGELOG.md](CHANGELOG.md)

## 🧩 Part of the PlanX ecosystem

This plugin is one of 15 open-source QGIS plugins for urban planning by the same author:

| Planning & analysis | CAD & production | 3D & visualization |
|---|---|---|
| [PlanX](https://github.com/YusufEminoglu/PlanX) — spatial-planning suite | [PlanX CAD Toolset](https://github.com/YusufEminoglu/PlanX-CAD) — drafting-grade CAD | [PlanX 3D City](https://github.com/YusufEminoglu/planx_3d_city) — Three.js city viewer |
| [GeoStats Lab](https://github.com/YusufEminoglu/planx_geostats) — spatial statistics | [EasyFillet](https://github.com/YusufEminoglu/EasyFillet) — tangent-arc fillet | [3D OSM Model](https://github.com/YusufEminoglu/osm_3d_model) — OSM → 3D city in browser |
| [Suitability Lab](https://github.com/YusufEminoglu/planx_suitability_lab) — raster MCDA | [Settlement Toolset](https://github.com/YusufEminoglu/PlanX-Settlement) — 9-stage settlement plans | [OSM Quick 3D](https://github.com/YusufEminoglu/osm_quick_3d) — OSM → native QGIS 3D |
| [DataCube Lab](https://github.com/YusufEminoglu/planx_datacube) — spatiotemporal cubes | [UIP Toolset](https://github.com/YusufEminoglu/PlanX-UIP) — Turkish master-plan automation | [Urban Procedural 3D](https://github.com/YusufEminoglu/planx_urban_procedural_3d) — parametric zoning lab |
| [Urban Resilience](https://github.com/YusufEminoglu/planx_urban_resilience) — 28 resilience tools | [ParcelFlux](https://github.com/YusufEminoglu/parcelflux) — parcel subdivision | [CartoLab](https://github.com/YusufEminoglu/planx_cartolab) — publication cartography |

## 📜 License & author

GPL-3.0 © [Yusuf Eminoğlu](https://github.com/YusufEminoglu) — Dokuz Eylül University, Department of City and Regional Planning. Bug reports and feature requests welcome in [Issues](https://github.com/YusufEminoglu/PlanX-UIP/issues).
