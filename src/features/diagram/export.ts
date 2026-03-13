export function exportMermaidSvgAsPng(svgElement: SVGSVGElement): void {
  const canvas = document.createElement("canvas");
  const scale = 4;

  const bbox = svgElement.getBBox();
  const transform = svgElement.getScreenCTM();
  if (!transform) return;

  const width = Math.ceil(bbox.width * transform.a);
  const height = Math.ceil(bbox.height * transform.d);
  canvas.width = width * scale;
  canvas.height = height * scale;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const svgData = new XMLSerializer().serializeToString(svgElement);
  const img = new Image();

  img.onload = () => {
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0, width, height);

    const anchor = document.createElement("a");
    anchor.download = "diagram.png";
    anchor.href = canvas.toDataURL("image/png", 1.0);
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
  };

  img.src =
    "data:image/svg+xml;base64," +
    btoa(unescape(encodeURIComponent(svgData)));
}

function downloadFile(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.download = filename;
  anchor.href = url;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function exportMermaidSvg(svgElement: SVGSVGElement): void {
  const svgData = new XMLSerializer().serializeToString(svgElement);
  downloadFile("diagram.svg", svgData, "image/svg+xml");
}

export function exportMermaidCode(mermaidCode: string): void {
  downloadFile("diagram.mmd", mermaidCode, "text/plain");
}

export function exportMermaidMarkdown(mermaidCode: string): void {
  const md = `# Repository Diagram\n\n\`\`\`mermaid\n${mermaidCode}\n\`\`\`\n`;
  downloadFile("diagram.md", md, "text/markdown");
}
