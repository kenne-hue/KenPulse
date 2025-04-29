# KenPulse - Smart City Reporting Platform

KenPulse is a web application that allows citizens to report urban issues in their communities. The platform enables users to submit reports with photos, track the status of their reports, and receive updates when issues are resolved.

## Features

- User authentication (sign up, login, profile management)
- Report submission with photos
- Report tracking and status updates
- Resolution proof submission
- Bilingual support (English and Swahili)
- Responsive design for mobile and desktop

## Tech Stack

- Backend: Python Flask
- Database: SQLite
- Frontend: HTML, CSS (Tailwind), JavaScript
- Authentication: Flask-Login
- File Upload: Flask-Uploads
- Email: Flask-Mail

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kenpulse.git
cd kenpulse
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following variables:
```
FLASK_APP=main.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 