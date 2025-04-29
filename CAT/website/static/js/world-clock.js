// World Clock functionality
class WorldClock {
    constructor() {
        this.timeZone = 'Africa/Nairobi'; // Kenya timezone
        this.clockElement = document.getElementById('world-clock');
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);
    }

    async updateClock() {
        try {
            const response = await fetch(`https://worldtimeapi.org/api/timezone/${this.timeZone}`);
            const data = await response.json();
            
            const date = new Date(data.datetime);
            const options = {
                timeZone: this.timeZone,
                hour12: true,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            };
            
            const formattedDate = date.toLocaleString('en-US', options);
            this.clockElement.textContent = formattedDate;
        } catch (error) {
            console.error('Error fetching time:', error);
            // Fallback to local time if API fails
            const date = new Date();
            this.clockElement.textContent = date.toLocaleString('en-US', {
                timeZone: this.timeZone,
                ...options
            });
        }
    }
}

// Initialize the clock when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WorldClock();
}); 