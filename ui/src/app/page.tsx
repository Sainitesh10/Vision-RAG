"use client";

import { useState } from "react";
import Sidebar from "@/components/layout/sidebar";
import ChatInterface from "@/components/chat/chat-interface";
import dynamic from "next/dynamic";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";

const PdfViewer = dynamic(() => import("@/components/pdf/pdf-viewer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-muted/10 text-muted-foreground animate-pulse text-sm">
      Loading Document Environment...
    </div>
  ),
});

export default function Home() {
  const [currentPdf, setCurrentPdf] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative dark">
      {/* Deep Space Background Blobs */}
      <div className="absolute top-0 -left-4 w-96 h-96 bg-purple-700 rounded-full mix-blend-screen filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-0 -right-4 w-96 h-96 bg-blue-700 rounded-full mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-96 h-96 bg-fuchsia-700 rounded-full mix-blend-screen filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>

      {/* Main Glass Container */}
      <div className="flex h-full w-full glass z-10 relative">
        {/* Falling Stars (Now inside the glass so they don't get blurred out!) */}
        <style>{`
          @keyframes shootingStarFall {
            0% { transform: translate(-50px, -50px) rotate(45deg) scale(0); opacity: 0; }
            10% { opacity: 1; scale: 1; }
            100% { transform: translate(120vw, 120vh) rotate(45deg) scale(1); opacity: 0; }
          }
          .star-base {
            position: absolute;
            width: 4px;
            height: 4px;
            background: #ffffff;
            border-radius: 50%;
            box-shadow: 0 0 15px 3px #ffffff;
            animation: shootingStarFall linear infinite;
          }
          .star-tail {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            right: 0;
            width: 150px;
            height: 2px;
            background: linear-gradient(to left, rgba(255,255,255,0), rgba(255,255,255,1));
          }
        `}</style>
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
          {/* Massive continuous random meteor shower array */}
          <div className="star-base" style={{ top: '-10%', left: '10%', animationDuration: '3s', animationDelay: '0s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-5%', left: '25%', animationDuration: '4s', animationDelay: '1.2s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '5%', left: '45%', animationDuration: '3.5s', animationDelay: '2.5s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-15%', left: '70%', animationDuration: '4.5s', animationDelay: '0.5s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '15%', left: '-10%', animationDuration: '3.2s', animationDelay: '1.8s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '35%', left: '-10%', animationDuration: '4.1s', animationDelay: '3.2s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-20%', left: '5%', animationDuration: '3.8s', animationDelay: '4.1s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '10%', left: '85%', animationDuration: '5s', animationDelay: '1.5s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '25%', left: '15%', animationDuration: '3.1s', animationDelay: '2.2s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-10%', left: '90%', animationDuration: '4.8s', animationDelay: '3.7s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '50%', left: '-20%', animationDuration: '3.6s', animationDelay: '0.8s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-5%', left: '55%', animationDuration: '4.2s', animationDelay: '5s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '30%', left: '40%', animationDuration: '3.9s', animationDelay: '6s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '0%', left: '100%', animationDuration: '4.6s', animationDelay: '2.8s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '15%', left: '60%', animationDuration: '3.3s', animationDelay: '4.5s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-25%', left: '20%', animationDuration: '5.2s', animationDelay: '1.1s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '40%', left: '75%', animationDuration: '3.7s', animationDelay: '5.5s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '5%', left: '-15%', animationDuration: '4.4s', animationDelay: '6.2s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-10%', left: '35%', animationDuration: '3.4s', animationDelay: '7s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '20%', left: '95%', animationDuration: '4.9s', animationDelay: '0.2s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '45%', left: '5%', animationDuration: '3.1s', animationDelay: '4.8s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '-15%', left: '80%', animationDuration: '4.3s', animationDelay: '2.9s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '10%', left: '25%', animationDuration: '3.8s', animationDelay: '5.8s' }}><div className="star-tail"></div></div>
          <div className="star-base" style={{ top: '55%', left: '-10%', animationDuration: '4.7s', animationDelay: '1.6s' }}><div className="star-tail"></div></div>
        </div>
        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden transition-opacity" 
            onClick={() => setSidebarOpen(false)} 
          />
        )}
        
        {/* Sidebar */}
        <div className={`
          fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 ease-in-out 
          md:relative md:translate-x-0 h-full shadow-2xl md:shadow-none glass-panel border-r border-white/5
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}>
          <Sidebar
            currentPdf={currentPdf}
            onSelectPdf={(pdf) => {
              setCurrentPdf(pdf);
              setSidebarOpen(false);
            }}
          />
        </div>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col lg:flex-row min-w-0 h-full overflow-hidden relative">
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between p-3 border-b border-white/5 glass-panel text-card-foreground shrink-0 z-10 shadow-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded-sm bg-primary shadow-[0_0_15px_rgba(255,255,255,0.5)]" />
              <span className="font-semibold text-white tracking-tight">Vision RAG</span>
            </div>
            <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)} className="h-8 w-8 text-white">
              <Menu className="w-5 h-5" />
            </Button>
          </div>

          {/* Middle Area: PDF Viewer */}
          <div className="flex-[1.2] lg:flex-1 relative border-b lg:border-b-0 lg:border-r border-white/5 bg-black/20 overflow-hidden flex flex-col min-h-0">
            <PdfViewer currentPdf={currentPdf} />
          </div>

          {/* Right Area: Chat Interface */}
          <div className="flex-1 lg:flex-none w-full lg:w-[400px] xl:w-[450px] relative glass-panel shadow-2xl z-20 flex flex-col min-h-0">
            <ChatInterface currentPdf={currentPdf} />
          </div>
        </main>
      </div>
    </div>
  );
}
