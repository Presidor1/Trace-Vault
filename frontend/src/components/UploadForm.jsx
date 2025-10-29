// tracevault/frontend/src/components/UploadForm.jsx

import React, { useState } from 'react';
import axios from 'axios';
import { FiUploadCloud, FiFile, FiCheckCircle, FiAlertTriangle, FiLoader } from 'react-icons/fi';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';

const UploadForm = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState(null); // 'success', 'error', 'info'

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setMessage(`File selected: ${selectedFile.name}`);
      setStatus('info');
    }
  };

  const handleUpload = async (event) => {
    event.preventDefault();
    if (!file) {
      setMessage('Please select an evidence file first.');
      setStatus('error');
      return;
    }

    setIsUploading(true);
    setMessage('Uploading file and queuing analysis...');
    setStatus('info');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.status === 202) {
        setMessage(`Success! Analysis job queued. Evidence ID: ${response.data.evidence_id}`);
        setStatus('success');
        // Pass the evidence ID back to the main page component
        onUploadSuccess(response.data.evidence_id); 
      } else {
        throw new Error(response.data.message || 'Unknown API response.');
      }
    } catch (error) {
      const errorMsg = error.response?.data?.message || error.message || 'A network error occurred.';
      setMessage(`Upload failed: ${errorMsg}`);
      setStatus('error');
      console.error('Upload Error:', error);
    } finally {
      setIsUploading(false);
      setFile(null); // Clear file input after attempt
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <FiCheckCircle className="text-success-green" />;
      case 'error':
        return <FiAlertTriangle className="text-error-red" />;
      case 'info':
      default:
        return <FiLoader className={`animate-spin ${isUploading ? 'inline' : 'hidden'}`} />;
    }
  };

  return (
    <div className="bg-primary-dark p-8 rounded-xl shadow-2xl w-full max-w-lg border border-accent-blue/30">
      <h2 className="text-3xl font-bold text-white mb-6 flex items-center">
        <FiUploadCloud className="mr-3 text-accent-blue" />
        Submit Evidence
      </h2>
      <form onSubmit={handleUpload}>
        <div className="mb-6">
          <label className="block text-secondary-light text-sm font-medium mb-2">
            Evidence File (Image/Video)
          </label>
          <div className="flex items-center justify-center w-full">
            <label
              htmlFor="dropzone-file"
              className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                file ? 'border-success-green bg-primary-dark/50' : 'border-secondary-light/50 hover:border-accent-blue bg-primary-dark/20'
              }`}
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                {file ? (
                  <>
                    <FiFile className="w-8 h-8 mb-3 text-success-green" />
                    <p className="mb-2 text-sm text-white font-medium">{file.name}</p>
                    <p className="text-xs text-secondary-light">Ready to upload.</p>
                  </>
                ) : (
                  <>
                    <FiUploadCloud className="w-10 h-10 mb-3 text-secondary-light" />
                    <p className="mb-2 text-sm text-white">
                      <span className="font-semibold">Click to upload</span> or drag and drop
                    </p>
                    <p className="text-xs text-secondary-light">
                      (PNG, JPG, MP4, MOV - Max 500MB)
                    </p>
                  </>
                )}
              </div>
              <input 
                id="dropzone-file" 
                type="file" 
                className="hidden" 
                onChange={handleFileChange} 
                accept="image/*,video/*"
              />
            </label>
          </div>
        </div>
        
        <button
          type="submit"
          className={`w-full py-3 px-4 font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center ${
            isUploading || !file
              ? 'bg-accent-blue/50 cursor-not-allowed'
              : 'bg-accent-blue hover:bg-accent-blue/80'
          }`}
          disabled={isUploading || !file}
        >
          {isUploading ? (
            <FiLoader className="w-5 h-5 mr-2 animate-spin" />
          ) : (
            <FiUploadCloud className="w-5 h-5 mr-2" />
          )}
          {isUploading ? 'Processing...' : 'Start Analysis'}
        </button>
      </form>

      {message && (
        <div className={`mt-4 p-3 rounded-lg text-sm flex items-center ${
            status === 'success' ? 'bg-success-green/10 text-success-green' :
            status === 'error' ? 'bg-error-red/10 text-error-red' :
            'bg-accent-blue/10 text-accent-blue'
        }`}>
          {getStatusIcon()}
          <span className="ml-2">{message}</span>
        </div>
      )}
    </div>
  );
};

export default UploadForm;
          
