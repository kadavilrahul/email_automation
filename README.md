# Product Recommendation Email Automation

## Overview

This project implements an automated product recommendation system that generates personalized product recommendation emails using the Gemini AI API.

## Prerequisites

- Python 3.8+
- Google Cloud account (for Gemini API)
- SMTP server access

## Virtual Environment Setup

### Creating a Virtual Environment

```bash
# Navigate to your project directory
cd ~/email_automation

# Create a virtual environment
python3 -m venv email_env

# Activate the virtual environment
source email_env/bin/activate

# To deactivate the virtual environment when done
# Simply run:
# deactivate
```

### Common Virtual Environment Troubleshooting

- Ensure you're using `python3` to create the venv
- Check the exact name of the virtual environment folder
- Verify the path to the `activate` script
- If you have multiple Python versions, specify the exact Python version:
  ```bash
  python3.8 -m venv email_env  # or python3.9, etc.
  ```

## Installation

1. With the virtual environment activated, install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `sample.env` to `.env`
```bash
cp sample.env .env
```

2. Update `.env` with your specific credentials:
- Database connection details
- SMTP server settings
- Gemini API key

### Required Environment Variables

- `IP_DATABASE`: Database server IP
- `DOMAIN`: Your domain name
- `DATABASE_NAME`: Database name
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password
- `DATABASE_TABLE_PREFIX`: Database table prefix
- `GEMINI_API`: Your Google Gemini API key
- `SMTP_SERVER`: SMTP server address
- `SMTP_PORT`: SMTP server port
- `SMTP_USERNAME`: SMTP username
- `SMTP_PASSWORD`: SMTP password
- `SENDER_EMAIL`: Email address used to send recommendations

## Usage

### Running the Script

```bash
python product_recommendations.py
```

### Customizing Recommendations

Modify the `get_recommendations` method in `product_recommendations.py` to implement more sophisticated recommendation logic.

## Logging

The script logs activities to `product_recommendations.log`, which includes:
- Successful email sends
- Recommendation generation
- Error tracking

## Error Handling

The script includes comprehensive error handling for:
- API request failures
- Email sending issues
- Recommendation generation problems

## Security Considerations

- Never commit `.env` file to version control
- Use environment variables for sensitive credentials
- Ensure SMTP and API credentials are kept confidential

## Dependencies

- `python-dotenv`: Environment variable management
- `requests`: HTTP requests
- `google-generativeai`: Gemini AI integration

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Troubleshooting

### Virtual Environment Issues
- Ensure you're in the correct project directory
- Verify Python version compatibility
- Check that all dependencies are installed in the virtual environment

## License

Specify your license here (e.g., MIT License)

## Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/product-recommendations](https://github.com/yourusername/product-recommendations)