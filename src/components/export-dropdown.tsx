import { CopyButton } from "./copy-button";
import { Image, FileImage, FileCode, FileText } from "lucide-react";
import { ActionButton } from "./action-button";

interface ExportDropdownProps {
  onCopy: () => void;
  lastGenerated: Date;
  onExportImage: () => void;
  onExportSvg: () => void;
  onExportMermaidCode: () => void;
  onExportMarkdown: () => void;
  isOpen: boolean;
}

export function ExportDropdown({
  onCopy,
  lastGenerated,
  onExportImage,
  onExportSvg,
  onExportMermaidCode,
  onExportMarkdown,
}: ExportDropdownProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-4">
        <ActionButton
          onClick={onExportImage}
          icon={Image}
          tooltipText="Download diagram as high-quality PNG"
          text="Download PNG"
        />
        <ActionButton
          onClick={onExportSvg}
          icon={FileImage}
          tooltipText="Download diagram as SVG vector graphic"
          text="Download SVG"
        />
        <ActionButton
          onClick={onExportMermaidCode}
          icon={FileCode}
          tooltipText="Download raw Mermaid.js code (.mmd)"
          text="Download Mermaid"
        />
        <ActionButton
          onClick={onExportMarkdown}
          icon={FileText}
          tooltipText="Download as Markdown with embedded Mermaid block"
          text="Download MD"
        />
        <CopyButton onClick={onCopy} />
      </div>

      <div className="flex items-center">
        <span className="text-sm text-gray-700 dark:text-neutral-300">
          Last generated: {lastGenerated.toLocaleString()}
        </span>
      </div>
    </div>
  );
}
