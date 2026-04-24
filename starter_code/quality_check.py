# ==========================================
# ROLE 3: OBSERVABILITY & QA ENGINEER
# ==========================================
# Task: Implement quality gates to reject corrupt data or logic discrepancies.

def run_quality_gate(document_dict):
    content = document_dict.get('content', '')
    
    # 1. Reject documents with 'content' length < 20 characters
    if len(content) < 20:
        return False
        
    # 2. Reject documents containing toxic/error strings (e.g., 'Null pointer exception')
    toxic_keywords = ["Null pointer exception", "OCR Error", "Traceback"]
    for keyword in toxic_keywords:
        if keyword in content:
            return False
            
    # 3. Flag discrepancies (e.g., if tax calculation comment says 8% but code says 10%)
    if "8%" in content and ("10%" in content or "0.10" in content):
        if "tax" in content.lower() or "vat" in content.lower():
            # Add 'discrepancy' to quality_flags
            if 'quality_flags' not in document_dict:
                document_dict['quality_flags'] = []
            if 'discrepancy' not in document_dict['quality_flags']:
                document_dict['quality_flags'].append('discrepancy')
            
            # According to WORKFLOW.md: log warning but still pass
            print(f"Warning: Logic discrepancy detected in document {document_dict.get('document_id')}")
            return True
    
    # Return True if pass, False if fail.
    return True


