import asyncio
import json
import requests
import time
from typing import List, Dict, Any

# Test Data - 10 Hinglish Transcripts
TEST_TRANSCRIPTS = [
    {
        "id": 1,
        "stage": "Pre-Due",
        "transcript": "Agent: Good morning, main Sameer bol raha hoon, Zenith Finance se. Sir, aapka personal loan EMI due date 30th hai. Just a reminder. Customer: Haan, haan, I know. Tum log har month call karte ho. Basically reminder ke liye call kiya hai na? Agent: Yes, sir, just confirming. Koi issue toh nahi hai payment mein? Kyunki aapka previous month bhi thoda late hua tha. Customer: Woh last time thoda salary cycle ka issue ho gaya tha, yaar. Lekin don't worry this time. Definitely ho jayega. Like, 29th tak clear kar dunga. Agent: Achha, sir, 29th ka PTP main confirm karun? Agar late hua toh impact will be on your credit report, you know. Customer: Theek hai, theek hai. Book kar lo. Aur frequent calls mat karna, please. Agent: Understood, sir. Thank you for the assurance.",
        "expected_intent": "Payment Reminder Response with PTP",
        "expected_call_purpose": "Payment Reminder",
        "expected_call_objective_met": True,
        "expected_key_results": "PTP for 29th",
        "expected_non_payment_reasons": "Previous salary cycle issue",
        "expected_sentiment_start": "Neutral",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Neutral",
        "expected_agent_performance_min": 7,
        "expected_action_required": True
    },
    {
        "id": 2,
        "stage": "Pre-Due",
        "transcript": "Agent: Namaste. Main Rita, Apex Bank se. Aapka credit card minimum due next week hai. Customer: Haan, minimum due toh theek hai, par listen, maine ek transaction dispute kiya hua hai. I purchased something online, but product nahi mila. Agent: Ma'am, woh dispute process alag chalta hai. Aapka due amount toh clear karna padega to avoid late charges. Customer: Toh, basically, main poora amount pay karun jab dispute pending hai? That's not fair, yaar! Agent: Ma'am, aap undisputed amount pay kar dijiye. Late fees toh nahi lagni chahiye na? Customer: Hmm... Theek hai. Main half payment kar deti hoon aaj evening tak. Baaki dispute resolution ke baad. Agent: Okay, ma'am. Half payment note kar liya hai. Please ensure.",
        "expected_intent": "Dispute Claim with Partial Payment",
        "expected_call_purpose": "Payment Reminder",
        "expected_call_objective_met": False,
        "expected_key_results": "Half payment commitment",
        "expected_non_payment_reasons": "Transaction dispute pending",
        "expected_sentiment_start": "Neutral",
        "expected_sentiment_end": "Negative",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 5,
        "expected_action_required": True
    },
    {
        "id": 3,
        "stage": "Post-Due (D+15)",
        "transcript": "Agent: Mr. Awasthi, aapka EMI 15 din se due hai. Reason kya hai? Humein immediate payment chahiye. Customer: Dekho, reason mat puchho, yaar. Thoda financial mismatch ho gaya hai suddenly. Woh company se payment late hua hai. Agent: Sir, kaun si company? Aur mismatch kitne din ka hai? Humein exact date chahiye. Otherwise, hum aapka account hard bucket mein shift kar denge. Customer: Hard bucket kya hota hai? Listen, main guarantee deta hoon, 15th tak. Paisa aa jayega pakka. Agent: Sir, 15th is too far. Aapko late payment fees aur interest dono lag rahe hain. Try to do it by Friday? Customer: Friday? Let me check... Achha, Friday ka promise karta hoon. No more calls till Friday, okay? Agent: PTP note ho gaya, sir.",
        "expected_intent": "Financial Difficulty with PTP",
        "expected_call_purpose": "Collection",
        "expected_call_objective_met": True,
        "expected_key_results": "PTP for Friday",
        "expected_non_payment_reasons": "Company payment delay, financial mismatch",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Neutral",
        "expected_agent_performance_min": 6,
        "expected_action_required": True
    },
    {
        "id": 4,
        "stage": "Post-Due (D+25)",
        "transcript": "Agent: Ms. Pooja, aapka card overdue hai. 25 din ho gaye hain. Aapki taraf se koi response nahi aaya. Customer: Haan, main jaanti hoon. Financial situation not good hai. Mera rent bhi due hai. Agent: Ma'am, hum aapki situation understand karte hain, but payment mandatory hai. Aap minimum due toh clear kar sakti hain? Customer: Minimum due bhi tough hai right now. Like, I can only pay half of the minimum due. Would that be okay? Agent: Ma'am, that's not ideal, par agar aap woh amount aaj de den toh we can temporarily hold the escalation. Customer: Theek hai. Debit card se payment kar rahi hoon abhi.",
        "expected_intent": "Financial Hardship with Partial Payment",
        "expected_call_purpose": "Collection",
        "expected_call_objective_met": False,
        "expected_key_results": "Half minimum due payment",
        "expected_non_payment_reasons": "Poor financial situation, rent due",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 7,
        "expected_action_required": True
    },
    {
        "id": 5,
        "stage": "Post-Due (D+30)",
        "transcript": "Agent: Mr. Singh, aapka loan 30 days se default mein hai. Hum final notice de rahe hain. Aap immediate action nahi le rahe. Customer: Listen, tum log roz call karke harass mat karo. Maine bola na, next month ki first week mein karunga! Agent: Sir, next month tak aapka account NPA ho jayega. You understand the implications? Aapka CIBIL score completely down ho jayega. Customer: Toh kya karun? Job nahi hai abhi. Agent: Sir, we need a formal letter for job loss. Otherwise, humein collection agency involve karni padegi. Give me a PTP date this week, or I initiate action. Customer: Uff... Monday ko chota amount karunga. Agent: Amount? Kitna? Customer: ₹5,000. Agent: Okay, ₹5,000 for Monday. We will monitor this closely.",
        "expected_intent": "Job Loss with Token Payment PTP",
        "expected_call_purpose": "Collection",
        "expected_call_objective_met": True,
        "expected_key_results": "₹5,000 payment PTP for Monday",
        "expected_non_payment_reasons": "Job loss, unemployment",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Negative",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 6,
        "expected_action_required": True
    },
    {
        "id": 6,
        "stage": "Recovery (D+75, Hardship)",
        "transcript": "Agent: Mr. Khan, 75 days ho chuke hain. Aapka total outstanding ₹3.5 lakh hai. Hum aapko legal notice send kar rahe hain. Customer: Bhai, legal notice kiska? Faltu ki baatein mat karo. Maine already two months se interest pay kar diya hai! Agent: Sir, aapne interest pay kiya hai, principal zero hai. Aap poora amount ek saath kab denge? Customer: Poora toh nahi de paunga. Like, can we do a one-time settlement (OTS)? Agent: OTS ke liye, sir, aapko minimum 25% upfront dena hoga. Aap eligible hain? Customer: 25% toh try kar sakta hoon. Email pe scheme ki details bhej do. Agent: Details send kar dete hain. But first, you have to commit to an upfront amount today.",
        "expected_intent": "Settlement Request (OTS)",
        "expected_call_purpose": "Recovery",
        "expected_call_objective_met": True,
        "expected_key_results": "OTS negotiation, 25% upfront commitment",
        "expected_non_payment_reasons": "Unable to pay full principal amount",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 7,
        "expected_action_required": True
    },
    {
        "id": 7,
        "stage": "Recovery (D+100, Hardship/Restructuring)",
        "transcript": "Agent: Ma'am, this is the final call from our side. Aapka account 100 days se default mein hai. Customer: I told you already, meri saheli ka accident ho gaya tha. All my savings went there. I am in deep trouble. Agent: Ma'am, we need proof of your hardship. Otherwise, hum account closure aur recovery start kar denge. Customer: Yaar, help karo na thodi. Can you convert this credit card due into a small EMI loan? Agent: Ma'am, restructuring is a process. Aapko hardship form fill karna padega and hospital bills submit karne honge. Customer: Achha, email karo saare forms right now. I will try to submit by tomorrow. Agent: Okay, forms are being sent. Please prioritize this.",
        "expected_intent": "Hardship & Restructuring Request",
        "expected_call_purpose": "Recovery",
        "expected_call_objective_met": True,
        "expected_key_results": "Restructuring forms to be sent, hospital bills required",
        "expected_non_payment_reasons": "Friend's accident, savings exhausted",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 8,
        "expected_action_required": True
    },
    {
        "id": 8,
        "stage": "Recovery (D+120, Conflict)",
        "transcript": "Agent: Mr. Varma, aapke ghar pe field agent visit kar raha hai aaj sham tak. Aap cooperate nahi kar rahe. Customer: Kon hai woh field agent? Tell him to not come! Maine tum logon ko permission nahi di hai. You are harassing me! Agent: Sir, this is part of the recovery procedure. Aap payment kyon nahi kar rahe, simple answer do. Customer: Payment next week tak confirm hai! Main already HR se baat kar chuka hoon. Agent: Sir, next week nahi. Give me a date, a clear date. Otherwise, the field team will proceed. Customer: Monday ko subah tak RTGS kar dunga. Confirm! Agent: Theek hai, Monday morning ka PTP. We will recall the field team for now.",
        "expected_intent": "Harassment Complaint with PTP",
        "expected_call_purpose": "Recovery",
        "expected_call_objective_met": True,
        "expected_key_results": "Field team recalled, Monday PTP commitment",
        "expected_non_payment_reasons": "Delay in HR processing",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 6,
        "expected_action_required": True
    },
    {
        "id": 9,
        "stage": "Recovery (D+90, Multiple Failed PTPs)",
        "transcript": "Agent: Ma'am, aapne last week do baar PTP diya, aur dono baar fail ho gaya. This is not acceptable. Customer: Dekho, main try kar rahi hoon. Mera boss salary delay kar raha hai. What can I do? Agent: Ma'am, excuses mat dijiye. Your credit report is already damaged. Aapke paas koi security hai, ya koi asset jisse aap fund arrange kar saken? Customer: Asset? No way! I can give you partial payment, you know, ₹15,000, but guarantee do ki no more calls for one month. Agent: We can agree to hold calls for 7 days after payment. Customer: Deal. 7 days no calls. Done.",
        "expected_intent": "Failed PTP with Partial Payment",
        "expected_call_purpose": "Collection",
        "expected_call_objective_met": False,
        "expected_key_results": "₹15,000 partial payment, 7-day call hold",
        "expected_non_payment_reasons": "Boss salary delay",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Negative",
        "expected_agent_performance_min": 6,
        "expected_action_required": True
    },
    {
        "id": 10,
        "stage": "Recovery (D+60, Settlement Inquiry)",
        "transcript": "Agent: Mr. Bansal, aapka loan 60 days past due hai. Hum legal process initiate kar rahe hain. Customer: Wait, wait! I want to settle. Kitna discount milega agar main lump sum de dun? Agent: Sir, settlement ke liye aapko eligibility check karni padegi. Aap total outstanding ka kitna % pay kar sakte hain? Customer: Like, main 50% de sakta hoon next 15 days mein. Agent: 50% is a good starting point. Hum aapki offer manager ko submit karte hain. But aapko processing fees upfront deni padegi. Customer: Processing fees kitni hogi? Tell me the total. Agent: Main aapko email pe detailed proposal bhejta hoon. Please check your email right now.",
        "expected_intent": "Settlement Inquiry",
        "expected_call_purpose": "Recovery",
        "expected_call_objective_met": True,
        "expected_key_results": "50% settlement offer, detailed proposal to be sent",
        "expected_non_payment_reasons": "Financial difficulty requiring settlement",
        "expected_sentiment_start": "Negative",
        "expected_sentiment_end": "Neutral",
        "expected_overall_sentiment": "Neutral",
        "expected_agent_performance_min": 8,
        "expected_action_required": True
    }
]

class PipelineValidator:
    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url
        self.results = []
    
    def test_api_connection(self) -> bool:
        """Test if the API is running and accessible"""
        try:
            response = requests.get(f"{self.api_url}/docs")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Send transcript to API and get insights"""
        try:
            payload = {"transcript": transcript}
            response = requests.post(
                f"{self.api_url}/analyze_call",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API returned status {response.status_code}: {response.text}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def evaluate_result(self, expected: Dict, actual: Dict) -> Dict[str, Any]:
        """Compare expected vs actual results"""
        if "error" in actual:
            return {
                "intent_match": False,
                "call_purpose_match": False,
                "call_objective_match": False,
                "sentiment_start_match": False,
                "sentiment_end_match": False,
                "overall_sentiment_match": False,
                "agent_performance_acceptable": False,
                "action_match": False,
                "error": actual["error"]
            }
        
        insights = actual.get("insights", {})
        
        # Extract actual values
        actual_intent = insights.get("customer_intent", "")
        actual_call_purpose = insights.get("call_purpose", "")
        actual_call_objective_met = insights.get("call_objective_met", False)
        actual_key_results = insights.get("key_results", "")
        actual_non_payment_reasons = insights.get("non_payment_reasons", "")
        actual_sentiment_start = insights.get("sentiment_start", "")
        actual_sentiment_end = insights.get("sentiment_end", "")
        actual_overall_sentiment = insights.get("overall_sentiment", "")
        actual_agent_rating = insights.get("agent_performance_rating", 0)
        actual_action = insights.get("action_required", False)
        
        # Flexible keyword-based matching
        intent_keywords = expected["expected_intent"].lower().split()
        intent_match = any(keyword in actual_intent.lower() for keyword in intent_keywords)
        
        purpose_keywords = expected["expected_call_purpose"].lower().split()
        call_purpose_match = any(keyword in actual_call_purpose.lower() for keyword in purpose_keywords)
        
        # Exact matches
        call_objective_match = actual_call_objective_met == expected["expected_call_objective_met"]
        sentiment_start_match = actual_sentiment_start == expected["expected_sentiment_start"]
        sentiment_end_match = actual_sentiment_end == expected["expected_sentiment_end"]
        overall_sentiment_match = actual_overall_sentiment == expected["expected_overall_sentiment"]
        action_match = actual_action == expected["expected_action_required"]
        
        # Agent performance (should meet minimum threshold)
        agent_performance_acceptable = actual_agent_rating >= expected["expected_agent_performance_min"]
        
        # Check if key results and non-payment reasons contain expected keywords
        key_results_keywords = expected["expected_key_results"].lower().split()
        key_results_match = any(keyword in actual_key_results.lower() for keyword in key_results_keywords)
        
        non_payment_keywords = expected["expected_non_payment_reasons"].lower().split()
        non_payment_match = any(keyword in actual_non_payment_reasons.lower() for keyword in non_payment_keywords)
        
        return {
            "intent_match": intent_match,
            "call_purpose_match": call_purpose_match,
            "call_objective_match": call_objective_match,
            "key_results_match": key_results_match,
            "non_payment_match": non_payment_match,
            "sentiment_start_match": sentiment_start_match,
            "sentiment_end_match": sentiment_end_match,
            "overall_sentiment_match": overall_sentiment_match,
            "agent_performance_acceptable": agent_performance_acceptable,
            "action_match": action_match,
            "actual_intent": actual_intent,
            "actual_call_purpose": actual_call_purpose,
            "actual_call_objective_met": actual_call_objective_met,
            "actual_key_results": actual_key_results,
            "actual_non_payment_reasons": actual_non_payment_reasons,
            "actual_sentiment_start": actual_sentiment_start,
            "actual_sentiment_end": actual_sentiment_end,
            "actual_overall_sentiment": actual_overall_sentiment,
            "actual_agent_rating": actual_agent_rating,
            "actual_action": actual_action,
            "expected_intent": expected["expected_intent"],
            "expected_call_purpose": expected["expected_call_purpose"],
            "expected_call_objective_met": expected["expected_call_objective_met"],
            "expected_key_results": expected["expected_key_results"],
            "expected_non_payment_reasons": expected["expected_non_payment_reasons"],
            "expected_sentiment_start": expected["expected_sentiment_start"],
            "expected_sentiment_end": expected["expected_sentiment_end"],
            "expected_overall_sentiment": expected["expected_overall_sentiment"],
            "expected_agent_performance_min": expected["expected_agent_performance_min"],
            "expected_action": expected["expected_action_required"]
        }
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and compile results"""
        print("🚀 Starting Conversational Insights Pipeline Validation")
        print("=" * 60)
        
        # Check API connection
        if not self.test_api_connection():
            print("❌ ERROR: API is not accessible. Make sure uvicorn server is running.")
            print("Run: uvicorn main:app --reload")
            return {"error": "API not accessible"}
        
        print("✅ API connection successful")
        print("\n📊 Processing transcripts...\n")
        
        # Process each transcript
        for i, test_case in enumerate(TEST_TRANSCRIPTS, 1):
            print(f"Test {i}/10: {test_case['stage']} (ID: {test_case['id']})")
            
            # Analyze transcript
            result = self.analyze_transcript(test_case['transcript'])
            
            # Evaluate result
            evaluation = self.evaluate_result(test_case, result)
            
            # Store result
            self.results.append({
                "test_id": test_case['id'],
                "stage": test_case['stage'],
                "evaluation": evaluation,
                "raw_result": result
            })
            
            # Print immediate feedback
            if "error" in evaluation:
                print(f"   ❌ ERROR: {evaluation['error']}")
            else:
                intent_status = "✅" if evaluation['intent_match'] else "❌"
                purpose_status = "✅" if evaluation['call_purpose_match'] else "❌"
                objective_status = "✅" if evaluation['call_objective_match'] else "❌"
                sentiment_status = "✅" if evaluation['overall_sentiment_match'] else "❌"
                agent_status = "✅" if evaluation['agent_performance_acceptable'] else "❌"
                action_status = "✅" if evaluation['action_match'] else "❌"
                
                print(f"   Intent: {intent_status} | Purpose: {purpose_status} | Objective: {objective_status}")
                print(f"   Sentiment: {sentiment_status} | Agent: {agent_status} | Action: {action_status}")
            
            # Rate limiting
            time.sleep(1)
        
        # Compile summary
        return self.compile_summary()
    
    def compile_summary(self) -> Dict[str, Any]:
        """Compile test results summary"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if "error" not in r['evaluation'])
        
        if successful_tests == 0:
            return {
                "summary": {
                    "total_tests": total_tests,
                    "successful_tests": 0,
                    "failed_tests": total_tests,
                    "success_rate": 0.0
                },
                "details": self.results
            }
        
        # Calculate accuracy metrics
        intent_accuracy = sum(1 for r in self.results 
                             if r['evaluation'].get('intent_match', False)) / successful_tests * 100
        call_purpose_accuracy = sum(1 for r in self.results 
                                   if r['evaluation'].get('call_purpose_match', False)) / successful_tests * 100
        call_objective_accuracy = sum(1 for r in self.results 
                                     if r['evaluation'].get('call_objective_match', False)) / successful_tests * 100
        key_results_accuracy = sum(1 for r in self.results 
                                  if r['evaluation'].get('key_results_match', False)) / successful_tests * 100
        non_payment_accuracy = sum(1 for r in self.results 
                                  if r['evaluation'].get('non_payment_match', False)) / successful_tests * 100
        sentiment_start_accuracy = sum(1 for r in self.results 
                                      if r['evaluation'].get('sentiment_start_match', False)) / successful_tests * 100
        sentiment_end_accuracy = sum(1 for r in self.results 
                                    if r['evaluation'].get('sentiment_end_match', False)) / successful_tests * 100
        overall_sentiment_accuracy = sum(1 for r in self.results 
                                        if r['evaluation'].get('overall_sentiment_match', False)) / successful_tests * 100
        agent_performance_accuracy = sum(1 for r in self.results 
                                        if r['evaluation'].get('agent_performance_acceptable', False)) / successful_tests * 100
        action_accuracy = sum(1 for r in self.results 
                             if r['evaluation'].get('action_match', False)) / successful_tests * 100
        
        # Stage-wise analysis
        stage_analysis = {}
        for result in self.results:
            stage = result['stage']
            if stage not in stage_analysis:
                stage_analysis[stage] = {'total': 0, 'successful': 0}
            
            stage_analysis[stage]['total'] += 1
            if "error" not in result['evaluation']:
                stage_analysis[stage]['successful'] += 1
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": (successful_tests / total_tests) * 100,
                "intent_accuracy": intent_accuracy,
                "call_purpose_accuracy": call_purpose_accuracy,
                "call_objective_accuracy": call_objective_accuracy,
                "key_results_accuracy": key_results_accuracy,
                "non_payment_accuracy": non_payment_accuracy,
                "sentiment_start_accuracy": sentiment_start_accuracy,
                "sentiment_end_accuracy": sentiment_end_accuracy,
                "overall_sentiment_accuracy": overall_sentiment_accuracy,
                "agent_performance_accuracy": agent_performance_accuracy,
                "action_accuracy": action_accuracy
            },
            "stage_analysis": stage_analysis,
            "details": self.results
        }
    
    def print_detailed_report(self, summary: Dict[str, Any]):
        """Print comprehensive test report"""
        print("\n" + "=" * 60)
        print("📈 PIPELINE VALIDATION REPORT")
        print("=" * 60)
        
        # Overall Summary
        summary_data = summary['summary']
        print(f"Total Tests: {summary_data['total_tests']}")
        print(f"Successful: {summary_data['successful_tests']}")
        print(f"Failed: {summary_data['failed_tests']}")
        print(f"Success Rate: {summary_data['success_rate']:.1f}%")
        
        if summary_data['successful_tests'] > 0:
            print(f"\nAccuracy Metrics:")
            print(f"Intent Recognition: {summary_data['intent_accuracy']:.1f}%")
            print(f"Call Purpose: {summary_data['call_purpose_accuracy']:.1f}%")
            print(f"Call Objective: {summary_data['call_objective_accuracy']:.1f}%")
            print(f"Key Results: {summary_data['key_results_accuracy']:.1f}%")
            print(f"Non-Payment Reasons: {summary_data['non_payment_accuracy']:.1f}%")
            print(f"Sentiment Start: {summary_data['sentiment_start_accuracy']:.1f}%")
            print(f"Sentiment End: {summary_data['sentiment_end_accuracy']:.1f}%")
            print(f"Overall Sentiment: {summary_data['overall_sentiment_accuracy']:.1f}%")
            print(f"Agent Performance: {summary_data['agent_performance_accuracy']:.1f}%")
            print(f"Action Detection: {summary_data['action_accuracy']:.1f}%")
        
        # Stage-wise Analysis
        if 'stage_analysis' in summary:
            print(f"\n📊 Stage-wise Performance:")
            for stage, data in summary['stage_analysis'].items():
                success_rate = (data['successful'] / data['total']) * 100
                print(f"  {stage}: {data['successful']}/{data['total']} ({success_rate:.1f}%)")
        
        # Detailed Results
        print(f"\n🔍 Detailed Results:")
        for result in summary['details']:
            print(f"\nTest {result['test_id']} - {result['stage']}:")
            evaluation = result['evaluation']
            
            if 'error' in evaluation:
                print(f"  ❌ Error: {evaluation['error']}")
            else:
                print(f"  Intent: {'✅' if evaluation['intent_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_intent'][:50]}..., Got: {evaluation['actual_intent'][:50]}...)")
                print(f"  Purpose: {'✅' if evaluation['call_purpose_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_call_purpose']}, Got: {evaluation['actual_call_purpose']})")
                print(f"  Objective Met: {'✅' if evaluation['call_objective_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_call_objective_met']}, Got: {evaluation['actual_call_objective_met']})")
                print(f"  Key Results: {'✅' if evaluation['key_results_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_key_results']}, Got: {evaluation['actual_key_results'][:50]}...)")
                print(f"  Non-Payment Reasons: {'✅' if evaluation['non_payment_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_non_payment_reasons']}, Got: {evaluation['actual_non_payment_reasons'][:50]}...)")
                print(f"  Sentiment Start→End: {'✅' if evaluation['sentiment_start_match'] else '❌'}→{'✅' if evaluation['sentiment_end_match'] else '❌'} " +
                      f"({evaluation['actual_sentiment_start']}→{evaluation['actual_sentiment_end']})")
                print(f"  Overall Sentiment: {'✅' if evaluation['overall_sentiment_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_overall_sentiment']}, Got: {evaluation['actual_overall_sentiment']})")
                print(f"  Agent Performance: {'✅' if evaluation['agent_performance_acceptable'] else '❌'} " +
                      f"(Min: {evaluation['expected_agent_performance_min']}/10, Got: {evaluation['actual_agent_rating']}/10)")
                print(f"  Action Required: {'✅' if evaluation['action_match'] else '❌'} " +
                      f"(Expected: {evaluation['expected_action']}, Got: {evaluation['actual_action']})")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if summary_data['success_rate'] < 80:
            print("  - Consider improving LLM prompt engineering")
            print("  - Add more context-specific examples in prompts")
        
        if summary_data.get('intent_accuracy', 0) < 70:
            print("  - Enhance intent recognition with domain-specific keywords")
        
        if summary_data.get('call_purpose_accuracy', 0) < 80:
            print("  - Improve call purpose classification with clearer categories")
        
        if summary_data.get('call_objective_accuracy', 0) < 75:
            print("  - Define clearer success criteria for call objectives")
        
        if summary_data.get('overall_sentiment_accuracy', 0) < 80:
            print("  - Fine-tune sentiment analysis for Hinglish expressions")
        
        if summary_data.get('agent_performance_accuracy', 0) < 70:
            print("  - Establish clearer agent performance evaluation criteria")
            print("  - Add specific examples of good vs poor agent behavior")
        
        if summary_data.get('action_accuracy', 0) < 85:
            print("  - Clarify action_required logic in business rules")
        
        if summary_data.get('key_results_accuracy', 0) < 75:
            print("  - Improve key results extraction with better pattern recognition")
        
        if summary_data.get('non_payment_accuracy', 0) < 75:
            print("  - Enhance non-payment reason detection with financial hardship keywords")


def main():
    """Main execution function"""
    print("Conversational Insights Pipeline - Hinglish Transcripts Validation")
    print("Please ensure your FastAPI server is running: uvicorn main:app --reload")
    input("Press Enter to start testing...")
    
    validator = PipelineValidator()
    summary = validator.run_comprehensive_test()
    
    if "error" in summary:
        print(f"❌ Test execution failed: {summary['error']}")
        return
    
    validator.print_detailed_report(summary)
    
    # Save results to file
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to 'test_results.json'")


if __name__ == "__main__":
    main()