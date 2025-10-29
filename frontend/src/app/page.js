// tracevault/frontend/src/app/page.js

"use client"; // Required for client-side functionality (state, hooks)

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import UploadForm from '../components/UploadForm';
import { FiTarget, FiCheckCircle, FiClock, FiXOctagon, FiAlertCircle } from 'react-icons/fi';
import ResultsViewer from '../components/ResultsViewer'; // We'll create this component next

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';
const POLL_INTERVAL = 5000; // Poll the status every 5 seconds

export default function Home() {
  const [evidenceId, setEvidenceId] = useState(null);
  const [analysisStatus, setAnalysisStatus] = useState(null); // PENDING, EXTRACTED, COMPLETE, FAILED
  const [reportData, setReportData] = useState(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);

  // Function to fetch the current analysis status
  const fetchStatus = useCallback(async (id) => {
    if (!id) return;

    setIsLoadingStatus(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/status/${id}`);
      const data = response.data;
      
      setAnalysisStatus(data.status);
      
      if (data.status === 'ANALYSIS_COMPLETE') {
        setReportData(data.report);
      } else if (data.status === 'FAILED') {
        setReportData(null);
      }
    } catch (error) {
      console.error('Error fetching status:', error);
      setAnalysisStatus('ERROR'); // Custom status for fetch failure
      setReportData(null);
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  // Effect for polling the status
  useEffect(() => {
    let intervalId;

    if (evidenceId && analysisStatus !== 'ANALYSIS_COMPLETE' && analysisStatus !== 'FAILED' && analysisStatus !== 'ERROR') {
      // Start polling
      intervalId = setInterval(() => {
        fetchStatus(evidenceId);
      }, POLL_INTERVAL);
    } else if (evidenceId && analysisStatus) {
      // Stop polling if complete or failed
      clearInterval(intervalId);
    }

    return () => clearInterval(intervalId); // Cleanup function
  }, [evidenceId, analysisStatus, fetchStatus]);

  // Handler for successful upload from the UploadForm
  const handleUploadSuccess = (id) => {
    setEvidenceId(id);
    setAnalysisStatus('PENDING');
    setReportData(null);
  };
  
  // Handler for resetting the process
  const resetAnalysis = () => {
      setEvidenceId(null);
      setAnalysisStatus(null);
      setReportData(null);
      setIsLoadingStatus(false);
  };

  const StatusIndicator = () => {
    let icon, color, message;

    if (!evidenceId) return null;
    
    switch (analysisStatus) {
      case 'ANALYSIS_COMPLETE':
        icon = <FiCheckCircle className="text-success-green w-6 h-6" />;
        color = 'bg-success-green/10 text-success-green';
        message = 'Analysis Complete. Report Available.';
        break;
      case 'FAILED':
      case 'ERROR':
        icon = <FiXOctagon className="text-error-red w-6 h-6" />;
        color = 'bg-error-red/10 text-error-red';
        message = 'Analysis Failed. Check server logs.';
        break;
      default: // PENDING, METADATA_EXTRACTED, FRAMES_EXTRACTED, etc.
        icon = <FiClock className={`w-6 h-6 ${isLoadingStatus ? 'animate-spin' : ''}`} />;
        color = 'bg-accent-blue/10 text-accent-blue';
        message = `Status: ${analysisStatus}... Polling for updates.`;
        break;
    }

    return (
      <div className={`p-4 rounded-lg flex items-center justify-between mt-8 w-full max-w-4xl shadow-md ${color}`}>
        <div className="flex items-center">
            {icon}
            <p className="ml-3 font-medium">{message}</p>
        </div>
        <button 
            onClick={resetAnalysis}
            className="text-sm font-semibold border border-current px-3 py-1 rounded-md hover:bg-white/10 transition-colors"
        >
            Start New
        </button>
      </div>
    );
  };


  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <h1 className="text-5xl font-extrabold text-white mb-4 flex items-center">
        <FiTarget className="mr-4 text-accent-blue" />
        TraceVault
      </h1>
      <p className="text-secondary-light mb-12 text-center text-lg">
        AI-Powered Digital Evidence and OSINT Aggregation Platform
      </p>

      {/* Main Content Area */}
      <div className="w-full max-w-4xl flex justify-center">
        {!evidenceId ? (
          // 1. Show Upload Form initially
          <UploadForm onUploadSuccess={handleUploadSuccess} />
        ) : (
          // 2. Show Status and Results Viewer
          <div className="w-full">
            <StatusIndicator />
            {analysisStatus === 'ANALYSIS_COMPLETE' && reportData ? (
                // We'll replace this with the actual ResultsViewer component next
                <ResultsViewer 
                    evidenceId={evidenceId} 
                    reportData={reportData} 
                />
            ) : (
                <div className="text-center p-8 mt-6 bg-primary-dark/50 rounded-lg">
                    <FiAlertCircle className="w-12 h-12 mx-auto text-secondary-light mb-4" />
                    <p className="text-secondary-light">Waiting for the backend workers to complete processing...</p>
                    <p className="text-sm mt-2 text-accent-blue/80">Evidence ID: **{evidenceId}**</p>
                </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
        }
