// tracevault/frontend/src/components/ResultsViewer.jsx

import React, { useState } from 'react';
import { FiMapPin, FiCpu, FiEye, FiUser, FiLink } from 'react-icons/fi';

// --- Reusable Component: Info Card ---
const ResultCard = ({ title, value, children }) => (
    <div className="bg-primary-dark/50 p-4 rounded-lg border border-accent-blue/20 h-full">
        <h3 className="text-lg font-semibold text-secondary-light mb-2 border-b border-secondary-light/20 pb-1">{title}</h3>
        {value && <p className="text-white break-words whitespace-pre-wrap">{value}</p>}
        {children}
    </div>
);

// --- Section 1: Metadata and OCR ---
const MetadataSection = ({ report }) => {
    const metadata = report?.metadata || {};
    const ocrText = report?.ocr_text || 'No text extracted.';
    
    // Convert metadata object into display array
    const metadataDisplay = Object.entries(metadata).map(([key, value]) => ({
        key: key.replace(/([a-z])([A-Z])/g, '$1 $2').toUpperCase(),
        value: typeof value === 'object' ? JSON.stringify(value) : String(value)
    }));

    // Filter for key metadata points
    const keyMetadata = metadataDisplay.filter(item => 
        item.key.includes('GPS') || item.key.includes('DATE') || item.key.includes('MODEL')
    ).slice(0, 5); // Take top 5 key items

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Key Metadata */}
            <div className="lg:col-span-1">
                <ResultCard title="Key Metadata Points">
                    {keyMetadata.length > 0 ? (
                        <ul className="space-y-2 text-sm">
                            {keyMetadata.map((item, index) => (
                                <li key={index} className="flex flex-col text-secondary-light">
                                    <span className="font-medium text-white">{item.key}</span>
                                    <span className="text-xs italic text-secondary-light/70">{item.value}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className='text-sm italic text-secondary-light/70'>No primary metadata found.</p>
                    )}
                </ResultCard>
            </div>
            
            {/* OCR Text */}
            <div className="lg:col-span-2">
                <ResultCard title="OCR Text Extraction (Signs, Notes, etc.)" value={ocrText}>
                    {ocrText === 'No text extracted.' && <p className='text-sm italic text-secondary-light/70'>Tesseract found no readable text.</p>}
                </ResultCard>
            </div>

            {/* Full Metadata Dump (Optional - could be a downloadable file in production) */}
            <div className="lg:col-span-3">
                 <ResultCard title="Full Metadata Dump">
                    <pre className="text-xs bg-primary-dark p-3 rounded-md overflow-x-auto text-green-400">
                        {JSON.stringify(metadata, null, 2)}
                    </pre>
                </ResultCard>
            </div>
        </div>
    );
};

// --- Section 2: Scene and Context ---
const SceneSection = ({ frames, report }) => {
    // NOTE: This assumes 'frames' is passed down from a detailed API call.
    // For now, we'll use a placeholder structure based on the current simplified report.
    const sceneScores = frames?.[0]?.scene_analysis?.classification_scores || {
        'Urban Street': 0.85, 
        'Residential Area': 0.10, 
        'Industrial Complex': 0.05 
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="lg:col-span-2">
                <ResultCard title="Scene Classification (Location Context)">
                    <ul className="space-y-3">
                        {Object.entries(sceneScores).sort(([, a], [, b]) => b - a).map(([scene, score]) => (
                            <li key={scene}>
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-white">{scene}</span>
                                    <span className="font-mono text-accent-blue">{`${(score * 100).toFixed(2)}%`}</span>
                                </div>
                                <div className="w-full bg-secondary-light/20 rounded-full h-2 mt-1">
                                    <div 
                                        className="bg-accent-blue h-2 rounded-full transition-all duration-700" 
                                        style={{ width: `${score * 100}%` }}
                                    ></div>
                                </div>
                            </li>
                        ))}
                    </ul>
                </ResultCard>
            </div>
             <p className='lg:col-span-2 text-sm text-secondary-light/70 italic'>
                 Showing scores for the primary image/frame. Multiple frames may yield varying scene scores.
             </p>
        </div>
    );
};

// --- Section 3: Identity and OSINT Matches ---
const IdentitySection = ({ faces }) => {
    // NOTE: This assumes 'faces' array is passed down, with each face containing 
    // the OSINT matches and attributes.
    const mockFaces = faces || [
        { 
            face_id: 'face-a', 
            attributes: { gender: 'Male', age: 35, emotion: 'Neutral' },
            osint_matches: [
                { platform: 'Twitter', profile_name: 'John Doe', source_url: '#', similarity_score: 0.92 },
                { platform: 'Public Web', profile_name: 'J. Doe Blog', source_url: '#', similarity_score: 0.85 }
            ]
        },
        { 
            face_id: 'face-b', 
            attributes: { gender: 'Female', age: 28, emotion: 'Happy' },
            osint_matches: []
        }
    ];
    
    return (
        <div className="space-y-6">
            <p className="text-secondary-light text-sm">{mockFaces.length} Face(s) detected across evidence.</p>
            
            {mockFaces.map((face, index) => (
                <div key={face.face_id} className="bg-primary-dark p-5 rounded-xl border border-error-red/30 shadow-xl">
                    <h3 className="text-xl font-bold text-error-red mb-3 flex items-center">
                        <FiUser className="mr-2" />
                        SUSPECT FACE #{index + 1}
                    </h3>
                    
                    {/* Face Attributes */}
                    <div className="grid grid-cols-2 gap-4 mb-4">
                        <ResultCard title="Estimated Attributes">
                            <ul className="text-sm space-y-1">
                                {Object.entries(face.attributes).map(([key, value]) => (
                                    <li key={key}><span className="font-medium text-secondary-light">{key}:</span> <span className="text-white">{value}</span></li>
                                ))}
                            </ul>
                        </ResultCard>
                        <ResultCard title="Face Embedding Vector">
                            <p className='text-xs font-mono text-secondary-light/70 overflow-hidden text-ellipsis'>
                                [ {face.embedding_vector?.slice(0, 5).join(', ')}... ] <br/> ({face.embedding_vector?.length || 512} dimensions)
                            </p>
                            <p className='text-xs mt-2 italic text-accent-blue'>Saved for future correlation.</p>
                        </ResultCard>
                    </div>

                    {/* OSINT Matches */}
                    <h4 className="text-lg font-semibold text-accent-blue mt-4 mb-3 border-t border-accent-blue/50 pt-3 flex items-center">
                        <FiLink className="mr-2" />
                        OSINT Cross-Matches ({face.osint_matches?.length || 0})
                    </h4>
                    {face.osint_matches && face.osint_matches.length > 0 ? (
                        <div className="space-y-3">
                            {face.osint_matches.map((match, matchIndex) => (
                                <div key={matchIndex} className="bg-primary-dark/70 p-3 rounded-lg flex justify-between items-center">
                                    <div>
                                        <p className="font-semibold text-white">{match.profile_name} - ({match.platform})</p>
                                        <a href={match.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-accent-blue hover:underline">
                                            {match.source_url}
                                        </a>
                                    </div>
                                    <span className="font-bold text-lg text-success-green">{`${(match.similarity_score * 100).toFixed(1)}%`}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className='text-sm italic text-secondary-light/70'>No OSINT matches found above threshold for this face.</p>
                    )}
                </div>
            ))}
        </div>
    );
};


// --- Main Results Viewer Component ---
const ResultsViewer = ({ evidenceId, reportData }) => {
    const [activeTab, setActiveTab] = useState('identity');

    // MOCK data structure based on the simplified report to display the UI
    const mockFullReport = {
        evidenceId: evidenceId,
        metadata: reportData?.metadata, // Passed from simplified report
        ocr_text: reportData?.ocr_text, // Passed from simplified report
        frames_analyzed: reportData?.frames_analyzed,
        // The detailed data structures expected from a dedicated full report API endpoint
        faces: null, 
        frames: [{
            frame_id: 1,
            scene_analysis: { classification_scores: { 'Urban Street': 0.85, 'Residential Area': 0.10, 'Industrial Complex': 0.05 } }
        }] 
    };

    const tabs = [
        { id: 'identity', name: 'Identity & OSINT', icon: FiUser, component: IdentitySection, data: { faces: mockFullReport.faces } },
        { id: 'metadata', name: 'Metadata & OCR', icon: FiCpu, component: MetadataSection, data: { report: mockFullReport } },
        { id: 'scene', name: 'Scene Context', icon: FiMapPin, component: SceneSection, data: { frames: mockFullReport.frames, report: mockFullReport } },
    ];

    const ActiveComponent = tabs.find(t => t.id === activeTab).component;
    const ActiveData = tabs.find(t => t.id === activeTab).data;


    return (
        <div className="mt-8 w-full">
            <div className="bg-primary-dark/70 p-6 rounded-t-xl border-t border-x border-accent-blue/30">
                <h2 className="text-2xl font-bold text-white mb-2">Analysis Report: {evidenceId}</h2>
                <p className="text-secondary-light text-sm">Status: Complete. {mockFullReport.frames_analyzed} frames analyzed.</p>
            </div>
            
            {/* Tabs Navigation */}
            <div className="flex border-b border-accent-blue/30 bg-primary-dark/70">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        className={`py-3 px-6 text-sm font-semibold transition-colors duration-200 flex items-center ${
                            activeTab === tab.id
                                ? 'text-white border-b-2 border-accent-blue bg-primary-dark/90'
                                : 'text-secondary-light hover:text-white/70 hover:bg-primary-dark/30'
                        }`}
                        onClick={() => setActiveTab(tab.id)}
                    >
                        <tab.icon className="w-4 h-4 mr-2" />
                        {tab.name}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div className="p-6 bg-primary-dark/70 rounded-b-xl shadow-2xl">
                <ActiveComponent {...ActiveData} />
            </div>
            
            {/* Final Disclaimer/Instructions */}
            <div className="mt-6 p-4 text-center text-sm bg-accent-blue/10 text-secondary-light rounded-lg italic">
                NOTE: This report is aggregated intelligence. Corroboration is required for legal admissibility.
            </div>
        </div>
    );
};

export default ResultsViewer;
