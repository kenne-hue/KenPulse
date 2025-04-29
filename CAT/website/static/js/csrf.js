// Function to get CSRF token from meta tag
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    if (!token) {
        console.error('CSRF token not found');
        return null;
    }
    return token;
}

// Function to add CSRF token to fetch options
function addCSRFToken(options = {}) {
    const token = getCSRFToken();
    if (!token) return options;

    const headers = options.headers || {};
    return {
        ...options,
        headers: {
            ...headers,
            'X-CSRFToken': token
        }
    };
}

// Override fetch to automatically include CSRF token for non-GET requests
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    if (options.method && options.method.toUpperCase() !== 'GET') {
        options = addCSRFToken(options);
    }
    return originalFetch(url, options);
}; 