import { useCallback } from "react";

import {
  exportMermaidSvgAsPng,
  exportMermaidSvg,
  exportMermaidCode,
  exportMermaidMarkdown,
} from "~/features/diagram/export";

export function useDiagramExport(diagram: string) {
  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(diagram);
  }, [diagram]);

  const getSvgElement = () => {
    const el = document.querySelector(".mermaid svg");
    return el instanceof SVGSVGElement ? el : null;
  };

  const handleExportImage = useCallback(() => {
    const svgElement = getSvgElement();
    if (!svgElement) return;
    exportMermaidSvgAsPng(svgElement);
  }, []);

  const handleExportSvg = useCallback(() => {
    const svgElement = getSvgElement();
    if (!svgElement) return;
    exportMermaidSvg(svgElement);
  }, []);

  const handleExportMermaidCode = useCallback(() => {
    if (!diagram) return;
    exportMermaidCode(diagram);
  }, [diagram]);

  const handleExportMarkdown = useCallback(() => {
    if (!diagram) return;
    exportMermaidMarkdown(diagram);
  }, [diagram]);

  return {
    handleCopy,
    handleExportImage,
    handleExportSvg,
    handleExportMermaidCode,
    handleExportMarkdown,
  };
}
