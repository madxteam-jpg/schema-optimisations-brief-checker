from typing import List, Optional
from pydantic import BaseModel, Field


class ExtractedBrief(BaseModel):
    client_name: Optional[str] = Field(default="N/A", description="Client or brand name mentioned in brief")
    target_page_type: str = Field(description="Type of page targeted e.g., Product, Article, Local Business, FAQ")
    primary_seo_objective: str = Field(description="Primary objective e.g., Rich Result eligibility, Entity graph, CTR boost")
    requested_schema_types: List[str] = Field(description="List of Schema.org types requested e.g., ['Product', 'AggregateRating']")
    specified_properties: List[str] = Field(description="Properties specifically requested e.g., ['author', 'offers', 'price']")
    data_sources_referenced: List[str] = Field(description="CMS fields, APIs, or database references provided in the brief")


class AuditIssue(BaseModel):
    category: str = Field(description="Category e.g., Technical Compliance, Gap Analysis, Field Mapping, Entity Nesting")
    severity: str = Field(description="Severity level: Blocker, Warning, or Opportunity")
    issue_title: str = Field(description="Short summary of the issue")
    explanation: str = Field(description="Detailed explanation of why this is an issue")
    recommendation: str = Field(description="Actionable step to fix or optimize the brief requirement")


class BriefAuditReport(BaseModel):
    overall_score: int = Field(description="Brief health & completeness score from 0 to 100")
    score_label: str = Field(description="Label e.g., 'Pass - Ready for Implementation', 'Needs Revision', 'Critical Flaws'")
    executive_summary: str = Field(description="High-level overview of the audit findings")
    extracted_brief: ExtractedBrief = Field(description="Structured summary of extracted brief information")
    audit_findings: List[AuditIssue] = Field(description="List of individual issues, warnings, and opportunities found")
    missing_mandatory_fields: List[str] = Field(description="Schema.org or Google Rich Result mandatory fields missing from brief")
