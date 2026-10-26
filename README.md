<div align="center">

<img src="icon.svg" width="96" alt="PlanX UIP Toolset icon"/>

# PlanX UIP Toolset

**Automated Uygulama İmar Planı (Turkish master plan) toolset for QGIS — rapid base layers and layouts in 8 stages (Processing).**

[![QGIS](https://img.shields.io/badge/QGIS-3.0%2B-93b023?logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/planx_uip_arac_seti/)
[![Documentation](https://img.shields.io/badge/📖_Reference_Manual-13a0a0)](https://geophilo.com/planx_uip_arac_seti/)
[![Version](https://img.shields.io/github/v/tag/YusufEminoglu/PlanX-UIP?label=version&color=blue)](https://gitlab.com/geophilo1/planx_uip_arac_seti/releases)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-orange)](LICENSE)
[![QGIS Plugin Hub](https://img.shields.io/badge/QGIS%20Hub-install-589632?logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/planx_uip_arac_seti/)

</div>

---

## 📖 Documentation

**[Comprehensive Academic Reference Manual](https://geophilo.com/planx_uip_arac_seti/)** — complete documentation of every feature, parameter, and workflow. Hosted on Web Documentation.


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

**From a release zip:** download the latest zip from [Releases](https://gitlab.com/geophilo1/planx_uip_arac_seti/releases) → `Plugins → Install from ZIP`.

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
| [PlanX](https://gitlab.com/geophilo1/planx_uip_arac_seti) — spatial-planning suite | [PlanX CAD Toolset](https://gitlab.com/geophilo1/planx_uip_arac_seti) — drafting-grade CAD | [PlanX 3D City](https://gitlab.com/geophilo1/planx_uip_arac_seti) — Three.js city viewer |
| [GeoStats Lab](https://gitlab.com/geophilo1/planx_uip_arac_seti) — spatial statistics | [EasyFillet](https://gitlab.com/geophilo1/planx_uip_arac_seti) — tangent-arc fillet | [3D OSM Model](https://gitlab.com/geophilo1/planx_uip_arac_seti) — OSM → 3D city in browser |
| [Suitability Lab](https://gitlab.com/geophilo1/planx_uip_arac_seti) — raster MCDA | [Settlement Toolset](https://gitlab.com/geophilo1/planx_uip_arac_seti) — 9-stage settlement plans | [OSM Quick 3D](https://gitlab.com/geophilo1/planx_uip_arac_seti) — OSM → native QGIS 3D |
| [DataCube Lab](https://gitlab.com/geophilo1/planx_uip_arac_seti) — spatiotemporal cubes | [UIP Toolset](https://gitlab.com/geophilo1/planx_uip_arac_seti) — Turkish master-plan automation | [Urban Procedural 3D](https://gitlab.com/geophilo1/planx_uip_arac_seti) — parametric zoning lab |
| [Urban Resilience](https://gitlab.com/geophilo1/planx_uip_arac_seti) — 28 resilience tools | [ParcelFlux](https://gitlab.com/geophilo1/planx_uip_arac_seti) — parcel subdivision | [CartoLab](https://gitlab.com/geophilo1/planx_uip_arac_seti) — publication cartography |

## 📜 License & author

GPL-3.0-or-later © [Yusuf Eminoğlu](https://github.com/YusufEminoglu) — Dokuz Eylül University, Department of City and Regional Planning. Bug reports and feature requests welcome in [Issues](https://gitlab.com/geophilo1/planx_uip_arac_seti/-/issues).
