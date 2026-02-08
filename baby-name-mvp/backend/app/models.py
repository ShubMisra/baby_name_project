from sqlalchemy import Column, Integer, String, DateTime, Text, func
from app.db import Base


class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(120), nullable=False)
    request_payload = Column(Text, nullable=False)   # JSON string
    response_payload = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)