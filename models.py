from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from datetime import datetime

Base = declarative_base()

class GroupService(Base):
    __tablename__ = "group_services"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'))
    service_id = Column(Integer, ForeignKey('services.id'))
    enabled = Column(Boolean, default=True)
    webhook_url = Column(Text)
    webhook_updated_at = Column(DateTime, nullable=True)
    status_changed_at = Column(DateTime, nullable=True)
    group = relationship("Group", back_populates="group_services")
    service = relationship("Service", back_populates="group_services")

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    color = Column(String)
    webhook_footer = Column(String)
    webhook_footer_img = Column(String)
    webhook_url = Column(Text)
    enabled = Column(Boolean, default=True)
    group_services = relationship("GroupService", back_populates="group")

class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    group_services = relationship("GroupService", back_populates="service")
